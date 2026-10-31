"""S25-B uçları (``/api/v1``): satınalma siparişi, teslim alma, iade, eşleşmemiş hızlı kabul.

İzinler: okuma ``satinalma:oku``; sipariş açma/iptal/kapatma ``satinalma:yaz`` (sipariş yalnız
ONAYLANMIŞ talepten açılır — onay ayrı izindir, görev ayrımı korunur); teslim alma ve iade
depo işidir, ``stok:yaz``. Her yazma denetime düşer; stok değişimi gerçek zamanlı yayınlanır.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.responses import basari
from app.kimlik.models import Kullanici
from app.modules.crm.models import Firma
from app.modules.stok import siparis_service as ss
from app.modules.stok.models import (
    Depo,
    Lokasyon,
    Malzeme,
    SatinalmaSiparisi,
    SatinalmaSiparisiKalemi,
    SatinalmaTalebi,
    TeslimAlma,
    TeslimAlmaKalemi,
)

router = APIRouter(tags=["Satınalma Siparişi"], dependencies=[Depends(modul_gerekli("stok"))])

Oku = Annotated[Kullanici, Depends(izin_gerekli("satinalma:oku"))]
Yaz = Annotated[Kullanici, Depends(izin_gerekli("satinalma:yaz"))]
StokOku = Annotated[Kullanici, Depends(izin_gerekli("stok:oku"))]
Depocu = Annotated[Kullanici, Depends(izin_gerekli("stok:yaz"))]
Oturum = Annotated[AsyncSession, Depends(get_session)]
TenantDep = Annotated[Tenant, Depends(tenant_cozumle)]


class SiparisKalemAyarDTO(BaseModel):
    talep_kalemi_id: int
    birim_fiyat: Decimal | None = Field(default=None, ge=0)
    fazla_teslim_toleransi_yuzde: Decimal = Field(default=Decimal(0), ge=0, le=100)


class SiparisOlusturDTO(BaseModel):
    talep_id: int
    tedarikci_firma_id: int
    beklenen_teslim_tarihi: date | None = None
    aciklama: str = Field(default="", max_length=1000)
    kalemler: list[SiparisKalemAyarDTO] = Field(default_factory=list)


class TeslimKalemDTO(BaseModel):
    siparis_kalemi_id: int
    miktar: Decimal = Field(gt=0)
    lot_no: str = Field(default="", max_length=60)
    birim: str | None = Field(default=None, max_length=20)
    lokasyon_id: int | None = None


class TeslimAlDTO(BaseModel):
    irsaliye_no: str = Field(min_length=1, max_length=40)
    fiili_tarih: datetime | None = None
    lokasyon_id: int | None = None
    aciklama: str = Field(default="", max_length=500)
    kalemler: list[TeslimKalemDTO] = Field(min_length=1)


class IadeKalemDTO(BaseModel):
    teslim_alma_kalemi_id: int
    miktar: Decimal = Field(gt=0)


class IadeDTO(BaseModel):
    irsaliye_no: str = Field(min_length=1, max_length=40)
    aciklama: str = Field(default="", max_length=500)
    kalemler: list[IadeKalemDTO] = Field(min_length=1)


class KapatDTO(BaseModel):
    neden: str = Field(min_length=3, max_length=500)


def _f(d: Decimal | None) -> float | None:
    return float(d) if d is not None else None


async def _lokasyon_etiketleri(db: AsyncSession, idler: set[int]) -> dict[int, str]:
    if not idler:
        return {}
    rows = (
        await db.execute(
            select(Lokasyon.id, Depo.kod, Lokasyon.kod)
            .join(Depo, Depo.id == Lokasyon.depo_id)
            .where(Lokasyon.id.in_(idler))
        )
    ).all()
    return {lid: f"{dkod} / {lkod}" for lid, dkod, lkod in rows}


def _ozet(
    s: SatinalmaSiparisi, firma_ad: str | None, kalemler: list[SatinalmaSiparisiKalemi]
) -> dict[str, Any]:
    toplam = sum((k.miktar for k in kalemler), Decimal(0))
    teslim = sum((min(k.teslim_alinan_miktar, k.miktar) for k in kalemler), Decimal(0))
    tutar = sum(
        (k.miktar * k.birim_fiyat for k in kalemler if k.birim_fiyat is not None), Decimal(0)
    )
    return {
        "id": s.id,
        "kod": s.kod,
        "talep_id": s.talep_id,
        "tedarikci_firma_id": s.tedarikci_firma_id,
        "tedarikci_ad": firma_ad,
        "durum": s.durum,
        "para_birimi": s.para_birimi,
        "beklenen_teslim_tarihi": s.beklenen_teslim_tarihi.isoformat()
        if s.beklenen_teslim_tarihi
        else None,
        "aciklama": s.aciklama,
        "kapanis_nedeni": s.kapanis_nedeni,
        "kalem_sayisi": len(kalemler),
        "toplam_tutar": float(tutar),
        "teslim_orani": float(teslim / toplam) if toplam > 0 else 0.0,
        "olusturma_tarihi": s.olusturma_tarihi.isoformat() if s.olusturma_tarihi else None,
    }


async def _detay(db: AsyncSession, s: SatinalmaSiparisi) -> dict[str, Any]:
    kalemler = await ss.kalemler(db, s.id)
    firma = await db.get(Firma, s.tedarikci_firma_id)
    malzemeler = {
        m.id: m
        for m in (
            await db.execute(
                select(Malzeme).where(Malzeme.id.in_([k.malzeme_id for k in kalemler] or [0]))
            )
        ).scalars()
    }
    teslimler = list(
        (
            await db.execute(
                select(TeslimAlma)
                .options(selectinload(TeslimAlma.kalemler))
                .where(TeslimAlma.siparis_id == s.id)
                .order_by(TeslimAlma.id)
            )
        ).scalars()
    )
    iade_toplam: dict[int, Decimal] = {}
    for t in teslimler:
        for tk in t.kalemler:
            if tk.iade_edilen_kalem_id is not None:
                iade_toplam[tk.iade_edilen_kalem_id] = (
                    iade_toplam.get(tk.iade_edilen_kalem_id, Decimal(0)) + tk.miktar
                )
    lok = await _lokasyon_etiketleri(db, {tk.lokasyon_id for t in teslimler for tk in t.kalemler})
    kalem_malzeme = {k.id: malzemeler.get(k.malzeme_id) for k in kalemler}

    def _kalem(k: SatinalmaSiparisiKalemi) -> dict[str, Any]:
        m = malzemeler.get(k.malzeme_id)
        return {
            "id": k.id,
            "malzeme_id": k.malzeme_id,
            "malzeme_kod": m.kod if m else None,
            "malzeme_ad": m.ad if m else None,
            "birim": m.birim if m else None,
            "lot_takipli": bool(m and m.lot_takipli),
            "miktar": float(k.miktar),
            "teslim_alinan_miktar": float(k.teslim_alinan_miktar),
            "kalan_miktar": float(max(k.miktar - k.teslim_alinan_miktar, Decimal(0))),
            "birim_fiyat": _f(k.birim_fiyat),
            "fazla_teslim_toleransi_yuzde": float(k.fazla_teslim_toleransi_yuzde),
        }

    def _teslim(t: TeslimAlma) -> dict[str, Any]:
        return {
            "id": t.id,
            "tur": t.tur,
            "irsaliye_no": t.irsaliye_no,
            "iade_edilen_id": t.iade_edilen_id,
            "fiili_tarih": t.fiili_tarih.isoformat(),
            "zamaninda": t.zamaninda,
            "aciklama": t.aciklama,
            "kalemler": [
                {
                    "id": tk.id,
                    "siparis_kalemi_id": tk.siparis_kalemi_id,
                    "malzeme_kod": (
                        mk.kod if (mk := kalem_malzeme.get(tk.siparis_kalemi_id)) else None
                    ),
                    "malzeme_ad": mk.ad if mk else None,
                    "birim": mk.birim if mk else None,
                    "miktar": float(tk.miktar),
                    "iade_edilen_miktar": float(iade_toplam.get(tk.id, Decimal(0))),
                    "lokasyon_id": tk.lokasyon_id,
                    "lokasyon": lok.get(tk.lokasyon_id),
                    "lot_no": tk.lot_no,
                    "fazla_teslim": tk.fazla_teslim,
                    "hizli_kabulden": tk.eslesen_hareket_id is not None,
                }
                for tk in t.kalemler
            ],
        }

    return {
        **_ozet(s, firma.ad if firma else None, kalemler),
        "kalemler": [_kalem(k) for k in kalemler],
        "teslimler": [_teslim(t) for t in teslimler],
    }


# ── Sipariş ──────────────────────────────────────────────────────────────────


@router.get("/satinalma-siparisleri", summary="Satınalma siparişleri")
async def siparisler(
    _k: Oku,
    db: Oturum,
    durum: str | None = None,
    tedarikci_firma_id: int | None = None,
    talep_id: int | None = None,
) -> dict[str, Any]:
    q = (
        select(SatinalmaSiparisi, Firma.ad)
        .join(Firma, Firma.id == SatinalmaSiparisi.tedarikci_firma_id)
        .order_by(SatinalmaSiparisi.id.desc())
        .limit(200)
    )
    if durum:
        q = q.where(SatinalmaSiparisi.durum == durum)
    if tedarikci_firma_id is not None:
        q = q.where(SatinalmaSiparisi.tedarikci_firma_id == tedarikci_firma_id)
    if talep_id is not None:
        q = q.where(SatinalmaSiparisi.talep_id == talep_id)
    rows = (await db.execute(q)).all()
    tum_kalemler = list(
        (
            await db.execute(
                select(SatinalmaSiparisiKalemi).where(
                    SatinalmaSiparisiKalemi.siparis_id.in_([s.id for s, _ in rows] or [0])
                )
            )
        ).scalars()
    )
    gruplu: dict[int, list[SatinalmaSiparisiKalemi]] = {}
    for k in tum_kalemler:
        gruplu.setdefault(k.siparis_id, []).append(k)
    return basari([_ozet(s, ad, gruplu.get(s.id, [])) for s, ad in rows])


@router.get("/satinalma-siparisleri/{siparis_id}", summary="Sipariş detayı + teslim geçmişi")
async def siparis_detay(siparis_id: int, _k: Oku, db: Oturum) -> dict[str, Any]:
    s = await db.get(SatinalmaSiparisi, siparis_id)
    if s is None:
        raise KaynakBulunamadi("Sipariş bulunamadı")
    return basari(await _detay(db, s))


@router.post("/satinalma-siparisleri", status_code=201, summary="Onaylı talepten sipariş aç")
async def siparis_olustur(govde: SiparisOlusturDTO, kullanici: Yaz, db: Oturum) -> dict[str, Any]:
    talep = (
        await db.execute(
            select(SatinalmaTalebi)
            .options(selectinload(SatinalmaTalebi.kalemler))
            .where(SatinalmaTalebi.id == govde.talep_id)
            .with_for_update()
        )
    ).scalar_one_or_none()
    if talep is None:
        raise KaynakBulunamadi("Talep bulunamadı")
    siparis = await ss.siparis_olustur(
        db,
        talep,
        tedarikci_firma_id=govde.tedarikci_firma_id,
        beklenen_teslim_tarihi=govde.beklenen_teslim_tarihi,
        aciklama=govde.aciklama,
        fiyatlar={
            k.talep_kalemi_id: k.birim_fiyat for k in govde.kalemler if k.birim_fiyat is not None
        },
        toleranslar={k.talep_kalemi_id: k.fazla_teslim_toleransi_yuzde for k in govde.kalemler},
        kullanici=kullanici,
    )
    await denetim_yaz(
        db,
        eylem="olustur",
        kaynak="satinalma_siparisi",
        kaynak_id=str(siparis.id),
        kullanici=kullanici,
        detay={"kod": siparis.kod, "talep_id": talep.id, "tedarikci": govde.tedarikci_firma_id},
    )
    return basari(await _detay(db, siparis), mesaj=f"Sipariş {siparis.kod} açıldı")


async def _elle_gecis(
    db: AsyncSession, siparis_id: int, hedef: str, kullanici: Kullanici, neden: str | None
) -> dict[str, Any]:
    s = await ss.siparis_kilitli(db, siparis_id)
    ss.siparis_gecisi(s, hedef, teslim_var=await ss.teslim_var_mi(db, s.id))
    s.kapanis_nedeni = neden
    await db.flush()
    await denetim_yaz(
        db,
        eylem=hedef,
        kaynak="satinalma_siparisi",
        kaynak_id=str(s.id),
        kullanici=kullanici,
        detay={"neden": neden} if neden else {},
    )
    return await _detay(db, s)


@router.post("/satinalma-siparisleri/{siparis_id}/iptal", summary="Siparişi iptal et")
async def siparis_iptal(siparis_id: int, kullanici: Yaz, db: Oturum) -> dict[str, Any]:
    return basari(
        await _elle_gecis(db, siparis_id, "iptal", kullanici, None), mesaj="Sipariş iptal edildi"
    )


@router.post("/satinalma-siparisleri/{siparis_id}/kapat", summary="Kısmi siparişi kapat")
async def siparis_kapat(
    siparis_id: int, govde: KapatDTO, kullanici: Yaz, db: Oturum
) -> dict[str, Any]:
    return basari(
        await _elle_gecis(db, siparis_id, "kapatildi", kullanici, govde.neden),
        mesaj="Sipariş kapatıldı; kalan miktar beklenmiyor",
    )


# ── Teslim alma & iade ───────────────────────────────────────────────────────


@router.post(
    "/satinalma-siparisleri/{siparis_id}/teslim-al",
    status_code=201,
    summary="İrsaliyeyle teslim al (kısmi destekli, idempotent)",
)
async def teslim_al(
    siparis_id: int,
    govde: TeslimAlDTO,
    kullanici: Depocu,
    db: Oturum,
    tenant: TenantDep,
    response: Response,
) -> dict[str, Any]:
    s = await ss.siparis_kilitli(db, siparis_id)
    teslim, yeni = await ss.teslim_al(
        db,
        s,
        irsaliye_no=govde.irsaliye_no.strip(),
        fiili_tarih=govde.fiili_tarih or datetime.now(UTC),
        lokasyon_id=govde.lokasyon_id,
        satirlar=[
            ss.TeslimSatiri(
                siparis_kalemi_id=k.siparis_kalemi_id,
                miktar=k.miktar,
                lot_no=k.lot_no.strip(),
                birim=k.birim,
                lokasyon_id=k.lokasyon_id,
            )
            for k in govde.kalemler
        ],
        aciklama=govde.aciklama,
        kullanici=kullanici,
    )
    if not yeni:
        response.status_code = 200
        return basari(await _detay(db, s), mesaj="Bu irsaliye zaten işlenmiş")
    satirlar = (
        await db.execute(select(TeslimAlmaKalemi).where(TeslimAlmaKalemi.teslim_id == teslim.id))
    ).scalars()
    satir_list = list(satirlar)
    await denetim_yaz(
        db,
        eylem="teslim_al",
        kaynak="satinalma_siparisi",
        kaynak_id=str(s.id),
        kullanici=kullanici,
        detay={
            "teslim_id": teslim.id,
            "irsaliye_no": teslim.irsaliye_no,
            "fazla_teslim": [tk.siparis_kalemi_id for tk in satir_list if tk.fazla_teslim],
            "hizli_kabul_eslesen": [
                tk.eslesen_hareket_id for tk in satir_list if tk.eslesen_hareket_id
            ],
        },
    )
    kalem_malzeme = {k.id: k.malzeme_id for k in await ss.kalemler(db, s.id)}
    for mid in {kalem_malzeme[tk.siparis_kalemi_id] for tk in satir_list}:
        await yayinla(tenant.slug, {"tur": "stok.hareket", "malzeme_id": mid})
    return basari(await _detay(db, s), mesaj=f"İrsaliye {teslim.irsaliye_no} teslim alındı")


@router.post(
    "/teslim-almalar/{teslim_id}/iade", status_code=201, summary="Teslimi (kısmen) iade et"
)
async def iade(
    teslim_id: int,
    govde: IadeDTO,
    kullanici: Depocu,
    db: Oturum,
    tenant: TenantDep,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    teslim = await db.get(TeslimAlma, teslim_id)
    if teslim is None:
        raise KaynakBulunamadi("Teslim kaydı bulunamadı")
    s = await ss.siparis_kilitli(db, teslim.siparis_id)
    if idempotency_key is not None:
        onceki = (
            await db.execute(
                select(TeslimAlma).where(TeslimAlma.idempotency_anahtari == idempotency_key)
            )
        ).scalar_one_or_none()
        if onceki is not None:
            response.status_code = 200
            return basari(await _detay(db, s), mesaj="İade zaten işlenmiş")
    kayit = await ss.iade_et(
        db,
        s,
        teslim,
        irsaliye_no=govde.irsaliye_no.strip(),
        satirlar=[
            ss.IadeSatiri(teslim_alma_kalemi_id=k.teslim_alma_kalemi_id, miktar=k.miktar)
            for k in govde.kalemler
        ],
        aciklama=govde.aciklama,
        kullanici=kullanici,
        idempotency_anahtari=idempotency_key,
    )
    await denetim_yaz(
        db,
        eylem="iade",
        kaynak="satinalma_siparisi",
        kaynak_id=str(s.id),
        kullanici=kullanici,
        detay={"iade_id": kayit.id, "teslim_id": teslim.id, "irsaliye_no": kayit.irsaliye_no},
    )
    await yayinla(tenant.slug, {"tur": "stok.hareket", "siparis_id": s.id})
    return basari(await _detay(db, s), mesaj="İade kaydedildi")


@router.get("/teslim-almalar/eslesmemis", summary="Siparişe bağlanmamış hızlı mal kabuller")
async def eslesmemis(_k: StokOku, db: Oturum) -> dict[str, Any]:
    rows = await ss.eslesmemis_hizli_kabuller(db)
    lok = await _lokasyon_etiketleri(db, {h.lokasyon_id for h, _ in rows if h.lokasyon_id})
    simdi = datetime.now(UTC)
    return basari(
        [
            {
                "hareket_id": h.id,
                "malzeme_id": m.id,
                "malzeme_kod": m.kod,
                "malzeme_ad": m.ad,
                "birim": m.birim,
                "miktar": float(h.miktar),
                "irsaliye_no": h.kaynak,
                "lokasyon": lok.get(h.lokasyon_id) if h.lokasyon_id else None,
                "lot_no": h.lot_no,
                "olusturma_tarihi": h.olusturma_tarihi.isoformat(),
                "bekleyen_gun": (simdi - h.olusturma_tarihi).days,
            }
            for h, m in rows
        ]
    )
