"""Satış uçları (``/api/v1``, S31 / ADR-0050).

Okuma ``satis:oku``, sipariş hazırlama/sevk ``satis:yaz``, onay (MRP tetiği) ve onaylı siparişi
iptal ``satis:onay``. Siparişi açan onaylayamaz (görev ayrımı).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, KaynakBulunamadi, YetkiHatasi
from app.core.responses import Zarf, basari, sayfali
from app.core.sorgu import siralama_uygula
from app.core.zaman import is_gunu
from app.kimlik.models import Kullanici
from app.modules.crm.models import Firma
from app.modules.satis import durum, service
from app.modules.satis.models import SatisSiparisi
from app.modules.uretim.models import Makine
from app.modules.urun.models import Urun

router = APIRouter(tags=["Satış"], dependencies=[Depends(modul_gerekli("satis"))])
Oturum = Annotated[AsyncSession, Depends(get_session)]
TenantDep = Annotated[Tenant, Depends(tenant_cozumle)]
Oku = Annotated[Kullanici, Depends(izin_gerekli("satis:oku"))]
Yaz = Annotated[Kullanici, Depends(izin_gerekli("satis:yaz"))]
Onay = Annotated[Kullanici, Depends(izin_gerekli("satis:onay"))]

_SIRALAMA = {
    "kod": SatisSiparisi.kod,
    "teslim_tarihi": SatisSiparisi.teslim_tarihi,
    "durum": SatisSiparisi.durum,
    "olusturma_tarihi": SatisSiparisi.olusturma_tarihi,
}


# --- DTO ----------------------------------------------------------------------------------------


class SatisKalemGirdiDTO(BaseModel):
    urun_id: int = Field(ge=1)
    miktar: Decimal = Field(gt=0, le=Decimal("1000000"), max_digits=18, decimal_places=3)
    birim_fiyat: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=4)


class SatisSiparisOlusturDTO(BaseModel):
    firma_id: int = Field(ge=1)
    teslim_tarihi: date
    kalemler: list[SatisKalemGirdiDTO] = Field(min_length=1, max_length=100)
    makine_id: int | None = Field(default=None, ge=1)
    talep_id: int | None = Field(default=None, ge=1)
    para_birimi: str = Field(default="TRY", pattern="^[A-Z]{3}$")
    aciklama: str = Field(default="", max_length=1000)


class SatisSiparisGuncelleDTO(BaseModel):
    teslim_tarihi: date | None = None
    kalemler: list[SatisKalemGirdiDTO] | None = Field(default=None, min_length=1, max_length=100)
    makine_id: int | None = Field(default=None, ge=1)
    aciklama: str | None = Field(default=None, max_length=1000)


class SatisOnayDTO(BaseModel):
    makine_id: int | None = Field(default=None, ge=1)


class SatisDurumDTO(BaseModel):
    durum: str


class SatisKalemCevapDTO(BaseModel):
    id: int
    sira: int
    urun_id: int
    urun_kod: str | None
    urun_ad: str | None
    miktar: float
    birim_fiyat: float | None


class MrpTetikDTO(BaseModel):
    tur: str
    id: int
    kod: str | None
    durum: str | None


class SatisSiparisCevapDTO(BaseModel):
    id: int
    kod: str
    firma_id: int
    firma_ad: str | None
    talep_id: int | None
    makine_id: int | None
    makine_kod: str | None
    durum: str
    teslim_tarihi: date
    gecikti: bool
    para_birimi: str
    aciklama: str
    tutar: float | None
    olusturan_kullanici_id: int | None
    onaylayan_kullanici_id: int | None
    olusturma_tarihi: datetime
    gecerli_hedefler: list[str]
    kalemler: list[SatisKalemCevapDTO]
    tetikler: list[MrpTetikDTO]


class MrpIhtiyacDTO(BaseModel):
    malzeme_id: int
    malzeme_kod: str | None
    malzeme_ad: str | None
    birim: str | None
    brut: float
    eldeki: float
    acik_tedarik: float
    ayrilmis: float
    kullanilabilir: float
    net: float


class SatisMrpDTO(BaseModel):
    siparis_id: int
    ihtiyaclar: list[MrpIhtiyacDTO]
    eksik_sayisi: int
    recetesiz_urunler: list[int]


class SatisOzetDTO(BaseModel):
    taslak: int
    onaylandi: int
    sevk_edildi: int
    kapandi: int
    geciken: int


# --- Yardımcılar ----------------------------------------------------------------------------------


def _kalemler(liste: list[SatisKalemGirdiDTO]) -> list[service.KalemGirdisi]:
    return [service.KalemGirdisi(k.urun_id, k.miktar, k.birim_fiyat) for k in liste]


async def _getir(db: AsyncSession, siparis_id: int) -> SatisSiparisi:
    s = await db.get(SatisSiparisi, siparis_id)
    if s is None:
        raise KaynakBulunamadi("Sipariş bulunamadı")
    return s


def _gecikti(s: SatisSiparisi) -> bool:
    return s.durum in ("taslak", "onaylandi") and s.teslim_tarihi < is_gunu()


async def _cevap(db: AsyncSession, s: SatisSiparisi, *, tetikli: bool = True) -> dict[str, Any]:
    await db.refresh(s, ["kalemler"])
    urunler = {
        u.id: u
        for u in (
            await db.execute(
                select(Urun).where(Urun.id.in_({k.urun_id for k in s.kalemler} or {0}))
            )
        ).scalars()
    }
    firma = await db.get(Firma, s.firma_id)
    makine = await db.get(Makine, s.makine_id) if s.makine_id else None
    fiyatli = [k for k in s.kalemler if k.birim_fiyat is not None]
    tutar = (
        float(sum((k.miktar * k.birim_fiyat for k in fiyatli), Decimal(0)))  # type: ignore[operator]
        if fiyatli and len(fiyatli) == len(s.kalemler)
        else None
    )
    return SatisSiparisCevapDTO(
        id=s.id,
        kod=s.kod,
        firma_id=s.firma_id,
        firma_ad=firma.ad if firma else None,
        talep_id=s.talep_id,
        makine_id=s.makine_id,
        makine_kod=makine.kod if makine else None,
        durum=s.durum,
        teslim_tarihi=s.teslim_tarihi,
        gecikti=_gecikti(s),
        para_birimi=s.para_birimi,
        aciklama=s.aciklama,
        tutar=tutar,
        olusturan_kullanici_id=s.olusturan_kullanici_id,
        onaylayan_kullanici_id=s.onaylayan_kullanici_id,
        olusturma_tarihi=s.olusturma_tarihi,
        gecerli_hedefler=sorted(durum.gecerli_hedefler(s.durum)),
        kalemler=[
            SatisKalemCevapDTO(
                id=k.id,
                sira=k.sira,
                urun_id=k.urun_id,
                urun_kod=urunler[k.urun_id].kod if k.urun_id in urunler else None,
                urun_ad=urunler[k.urun_id].ad if k.urun_id in urunler else None,
                miktar=float(k.miktar),
                birim_fiyat=float(k.birim_fiyat) if k.birim_fiyat is not None else None,
            )
            for k in s.kalemler
        ],
        tetikler=[MrpTetikDTO(**t) for t in await service.tetikler(db, s.id)] if tetikli else [],
    ).model_dump()


# --- Uçlar ----------------------------------------------------------------------------------------


@router.get(
    "/satis-siparisleri",
    response_model=Zarf[list[SatisSiparisCevapDTO]],
    summary="Siparişleri listele",
)
async def siparis_listele(
    _k: Oku,
    db: Oturum,
    _t: TenantDep,
    sayfa: int = 1,
    adet: int = 20,
    durum_: Annotated[str | None, Query(alias="durum", max_length=20)] = None,
    firma_id: int | None = None,
    geciken: bool = False,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa, adet = max(sayfa, 1), min(max(adet, 1), 100)
    kosullar: list[Any] = []
    if durum_:
        kosullar.append(SatisSiparisi.durum == durum_)
    if firma_id is not None:
        kosullar.append(SatisSiparisi.firma_id == firma_id)
    if geciken:
        kosullar += [
            SatisSiparisi.durum.in_(("taslak", "onaylandi")),
            SatisSiparisi.teslim_tarihi < is_gunu(),
        ]
    if arama:
        kalip = f"%{arama}%"
        kosullar.append(or_(SatisSiparisi.kod.ilike(kalip), Firma.ad.ilike(kalip)))
    sorgu = cast(
        "Select[Any]",
        select(SatisSiparisi).join(Firma, Firma.id == SatisSiparisi.firma_id).where(*kosullar),
    )
    toplam = await db.scalar(
        select(func.count())
        .select_from(SatisSiparisi)
        .join(Firma, Firma.id == SatisSiparisi.firma_id)
        .where(*kosullar)
    )
    sorgu = siralama_uygula(
        sorgu,
        siralama=siralama,
        yon=yon,
        izinli=_SIRALAMA,
        varsayilan=SatisSiparisi.id,
        varsayilan_yon="desc",
    )
    kayitlar = (await db.execute(sorgu.offset((sayfa - 1) * adet).limit(adet))).scalars().all()
    return sayfali(
        [await _cevap(db, s, tetikli=False) for s in kayitlar],
        sayfa=sayfa,
        adet=adet,
        toplam=int(toplam or 0),
    )


@router.get("/satis/ozet", response_model=Zarf[SatisOzetDTO], summary="Satış özeti")
async def satis_ozet(_k: Oku, db: Oturum, _t: TenantDep) -> dict[str, Any]:
    sayim = dict(
        (
            await db.execute(
                select(SatisSiparisi.durum, func.count()).group_by(SatisSiparisi.durum)
            )
        ).all()
    )
    geciken = await db.scalar(
        select(func.count())
        .select_from(SatisSiparisi)
        .where(
            SatisSiparisi.durum.in_(("taslak", "onaylandi")),
            SatisSiparisi.teslim_tarihi < is_gunu(),
        )
    )
    return basari(
        SatisOzetDTO(
            taslak=int(sayim.get("taslak", 0)),
            onaylandi=int(sayim.get("onaylandi", 0)),
            sevk_edildi=int(sayim.get("sevk_edildi", 0)),
            kapandi=int(sayim.get("kapandi", 0)),
            geciken=int(geciken or 0),
        ).model_dump(),
        mesaj="Satış özeti",
    )


@router.post(
    "/satis-siparisleri",
    response_model=Zarf[SatisSiparisCevapDTO],
    status_code=201,
    summary="Satış siparişi hazırla (taslak)",
)
async def siparis_olustur(
    govde: SatisSiparisOlusturDTO, k: Yaz, db: Oturum, _t: TenantDep
) -> dict[str, Any]:
    await service.firma_dogrula(db, govde.firma_id)
    await service.makine_dogrula(db, govde.makine_id)
    kalemler = _kalemler(govde.kalemler)
    await service.urunleri_dogrula(db, kalemler)
    if govde.talep_id is not None:
        await service.talep_dogrula(db, govde.talep_id, govde.firma_id)
    s = SatisSiparisi(
        kod=service.gecici_kod(),
        firma_id=govde.firma_id,
        talep_id=govde.talep_id,
        makine_id=govde.makine_id,
        teslim_tarihi=govde.teslim_tarihi,
        para_birimi=govde.para_birimi,
        aciklama=govde.aciklama,
        olusturan_kullanici_id=k.id,
    )
    service.kalemleri_kur(s, kalemler)
    db.add(s)
    await db.flush()
    s.kod = service.kalici_kod(s)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="satis_siparisi", kaynak_id=str(s.id), kullanici=k
    )
    return basari(await _cevap(db, s), mesaj="Sipariş taslağı oluşturuldu")


@router.get(
    "/satis-siparisleri/{siparis_id}",
    response_model=Zarf[SatisSiparisCevapDTO],
    summary="Sipariş detayı",
)
async def siparis_detay(siparis_id: int, _k: Oku, db: Oturum, _t: TenantDep) -> dict[str, Any]:
    return basari(await _cevap(db, await _getir(db, siparis_id)), mesaj="Sipariş")


@router.put(
    "/satis-siparisleri/{siparis_id}",
    response_model=Zarf[SatisSiparisCevapDTO],
    summary="Taslak siparişi düzenle",
)
async def siparis_guncelle(
    siparis_id: int, govde: SatisSiparisGuncelleDTO, k: Yaz, db: Oturum, _t: TenantDep
) -> dict[str, Any]:
    s = await service.siparis_kilitle(db, siparis_id)
    if s.durum not in durum.DUZENLENEBILIR:
        raise CakismaHatasi("Yalnız taslak sipariş düzenlenir")
    if govde.makine_id is not None:
        await service.makine_dogrula(db, govde.makine_id)
        s.makine_id = govde.makine_id
    if govde.teslim_tarihi is not None:
        s.teslim_tarihi = govde.teslim_tarihi
    if govde.aciklama is not None:
        s.aciklama = govde.aciklama
    if govde.kalemler is not None:
        kalemler = _kalemler(govde.kalemler)
        await service.urunleri_dogrula(db, kalemler)
        service.kalemleri_kur(s, kalemler)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="satis_siparisi", kaynak_id=str(s.id), kullanici=k
    )
    return basari(await _cevap(db, s), mesaj="Sipariş güncellendi")


@router.get(
    "/satis-siparisleri/{siparis_id}/mrp",
    response_model=Zarf[SatisMrpDTO],
    summary="Malzeme ihtiyaç planı (önizleme)",
)
async def siparis_mrp(siparis_id: int, _k: Oku, db: Oturum, _t: TenantDep) -> dict[str, Any]:
    s = await _getir(db, siparis_id)
    sonuc = await service.mrp_hesapla(db, s)
    malzemeler = await service.malzeme_bilgisi(db, {i.malzeme_id for i in sonuc.ihtiyaclar})
    return basari(
        SatisMrpDTO(
            siparis_id=s.id,
            ihtiyaclar=[
                MrpIhtiyacDTO(
                    malzeme_id=i.malzeme_id,
                    malzeme_kod=malzemeler[i.malzeme_id].kod
                    if i.malzeme_id in malzemeler
                    else None,
                    malzeme_ad=malzemeler[i.malzeme_id].ad if i.malzeme_id in malzemeler else None,
                    birim=malzemeler[i.malzeme_id].birim if i.malzeme_id in malzemeler else None,
                    brut=float(i.brut),
                    eldeki=float(i.eldeki),
                    acik_tedarik=float(i.acik_tedarik),
                    ayrilmis=float(i.ayrilmis),
                    kullanilabilir=float(i.kullanilabilir),
                    net=float(i.net),
                )
                for i in sonuc.ihtiyaclar
            ],
            eksik_sayisi=len(sonuc.eksikler),
            recetesiz_urunler=sonuc.recetesiz,
        ).model_dump(),
        mesaj="MRP",
    )


@router.post(
    "/satis-siparisleri/{siparis_id}/onayla",
    response_model=Zarf[SatisSiparisCevapDTO],
    summary="Siparişi onayla: MRP iş emri + satınalma talebi açar",
)
async def siparis_onayla(
    siparis_id: int, govde: SatisOnayDTO, k: Onay, db: Oturum, _t: TenantDep
) -> dict[str, Any]:
    s, tetik = await service.siparis_onayla(db, siparis_id, k, govde.makine_id)
    await denetim_yaz(
        db,
        eylem="onayla",
        kaynak="satis_siparisi",
        kaynak_id=str(s.id),
        kullanici=k,
        detay=service.tetik_govdesi(s, tetik),
    )
    return basari(await _cevap(db, s), mesaj="Sipariş onaylandı, üretim ve satınalma tetiklendi")


@router.post(
    "/satis-siparisleri/{siparis_id}/durum",
    response_model=Zarf[SatisSiparisCevapDTO],
    summary="Sevk / kapat / iptal",
)
async def siparis_durum(
    siparis_id: int, govde: SatisDurumDTO, k: Yaz, db: Oturum, _t: TenantDep
) -> dict[str, Any]:
    s = await service.siparis_kilitle(db, siparis_id)
    if govde.durum == "onaylandi":
        raise CakismaHatasi("Onay ayrı uçtan yapılır: /satis-siparisleri/{id}/onayla")
    service.gecis_dogrula(s, govde.durum)
    if govde.durum == "iptal" and s.durum == "onaylandi" and not k.izin_var("satis:onay"):
        raise YetkiHatasi("Onaylı siparişi yalnız satış onaylayan iptal edebilir")
    onceki = s.durum
    s.durum = govde.durum
    await db.flush()
    await denetim_yaz(
        db,
        eylem=f"durum:{govde.durum}",
        kaynak="satis_siparisi",
        kaynak_id=str(s.id),
        kullanici=k,
        detay={"onceki": onceki},
    )
    return basari(await _cevap(db, s), mesaj="Sipariş durumu güncellendi")
