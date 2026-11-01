"""Finans uçları (``/api/v1``, S29 / ADR-0048).

Okuma ``finans:oku``; fatura hazırlama, tahsilat ``finans:yaz``; fatura kesme/iade/iptal ve
firmaya giden **ödeme** ``finans:onay`` (para çıkışı ve cariye işleme onay ister). Hazırlayan
kişi kendi faturasını kesemez.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Header, Response
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
from app.modules.entegrasyon.deps import api_izin_gerekli
from app.modules.entegrasyon.models import ApiAnahtari
from app.modules.finans import hesap, maliyet, service
from app.modules.finans.fatura_pdf import FaturaPdfKalem, fatura_pdf
from app.modules.finans.models import CariHareket, CariHesap, Fatura, Odeme
from app.modules.finans.schemas import (
    CariEkstreDTO,
    CariHareketCevapDTO,
    CariHesapCevapDTO,
    EFaturaDisDTO,
    FaturaCevapDTO,
    FaturaGuncelleDTO,
    FaturaKalemiCevapDTO,
    FaturaKalemiGirdiDTO,
    FaturaOlusturDTO,
    FinansOzetDTO,
    GibDurumDTO,
    IsEmriMaliyetiDTO,
    MaliyetKalemiDTO,
    NedenDTO,
    OdemeCevapDTO,
    OdemeOlusturDTO,
    YaslandirmaDTO,
    YaslandirmaFirmaDTO,
    YaslandirmaYonuDTO,
)
from app.modules.stok.siparis_pdf import PdfFirma

router = APIRouter(tags=["Finans"], dependencies=[Depends(modul_gerekli("finans"))])

Oturum = Annotated[AsyncSession, Depends(get_session)]
TenantDep = Annotated[Tenant, Depends(tenant_cozumle)]
Oku = Annotated[Kullanici, Depends(izin_gerekli("finans:oku"))]
Yaz = Annotated[Kullanici, Depends(izin_gerekli("finans:yaz"))]
Onay = Annotated[Kullanici, Depends(izin_gerekli("finans:onay"))]

_FATURA_SIRALAMA = {
    "kod": Fatura.kod,
    "fatura_tarihi": Fatura.fatura_tarihi,
    "vade_tarihi": Fatura.vade_tarihi,
    "genel_toplam": Fatura.genel_toplam,
    "durum": Fatura.durum,
}


def _f(v: Decimal | None) -> float:
    return float(v or 0)


def _kalemler(govde: list[FaturaKalemiGirdiDTO]) -> list[service.KalemGirdisi]:
    return [
        service.KalemGirdisi(
            aciklama=k.aciklama,
            miktar=k.miktar,
            birim=k.birim,
            birim_fiyat=k.birim_fiyat,
            kdv_orani=k.kdv_orani,
            malzeme_id=k.malzeme_id,
        )
        for k in govde
    ]


def _fatura_cevap(f: Fatura, firma_ad: str) -> dict[str, Any]:
    acik = hesap.acik_tutar(f.genel_toplam, f.odenen_tutar)
    return FaturaCevapDTO(
        id=f.id,
        kod=f.kod,
        tur=f.tur,
        firma_id=f.firma_id,
        firma_ad=firma_ad,
        durum=f.durum,
        fatura_tarihi=f.fatura_tarihi,
        vade_tarihi=f.vade_tarihi,
        para_birimi=f.para_birimi,
        ara_toplam=_f(f.ara_toplam),
        kdv_toplam=_f(f.kdv_toplam),
        genel_toplam=_f(f.genel_toplam),
        odenen_tutar=_f(f.odenen_tutar),
        acik_tutar=_f(acik),
        vadesi_gecti=f.durum == "kesildi" and acik > 0 and f.vade_tarihi < is_gunu(),
        aciklama=f.aciklama,
        iade_nedeni=f.iade_nedeni,
        iptal_nedeni=f.iptal_nedeni,
        satinalma_siparisi_id=f.satinalma_siparisi_id,
        olusturan_kullanici_id=f.olusturan_kullanici_id,
        kesen_kullanici_id=f.kesen_kullanici_id,
        kesim_tarihi=f.kesim_tarihi,
        ettn=str(f.ettn),
        senaryo=f.senaryo,
        gib_durumu=f.gib_durumu,
        olusturma_tarihi=f.olusturma_tarihi,
        kalemler=[
            FaturaKalemiCevapDTO(
                id=k.id,
                sira=k.sira,
                aciklama=k.aciklama,
                malzeme_id=k.malzeme_id,
                miktar=float(k.miktar),
                birim=k.birim,
                birim_fiyat=float(k.birim_fiyat),
                kdv_orani=k.kdv_orani,
                satir_tutari=_f(k.satir_tutari),
                kdv_tutari=_f(k.kdv_tutari),
            )
            for k in f.kalemler
        ],
    ).model_dump()


async def _firma_ad(db: AsyncSession, firma_id: int) -> str:
    return (await db.scalar(select(Firma.ad).where(Firma.id == firma_id))) or "—"


async def _fatura_getir(db: AsyncSession, fatura_id: int) -> Fatura:
    f = await db.get(Fatura, fatura_id)
    if f is None:
        raise KaynakBulunamadi("Fatura bulunamadı")
    return f


async def _fatura_yanit(db: AsyncSession, f: Fatura, mesaj: str) -> dict[str, Any]:
    await db.refresh(f, ["kalemler"])
    return basari(_fatura_cevap(f, await _firma_ad(db, f.firma_id)), mesaj=mesaj)


# ── Faturalar ────────────────────────────────────────────────────────────────


@router.get("/faturalar", response_model=Zarf[list[FaturaCevapDTO]], summary="Faturaları listele")
async def fatura_listele(
    _k: Oku,
    db: Oturum,
    _t: TenantDep,
    sayfa: int = 1,
    adet: int = 20,
    tur: str | None = None,
    durum: str | None = None,
    firma_id: int | None = None,
    vadesi_gecmis: bool = False,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa, adet = max(sayfa, 1), min(max(adet, 1), 100)
    kosullar: list[Any] = []
    if tur:
        kosullar.append(Fatura.tur == tur)
    if durum:
        kosullar.append(Fatura.durum == durum)
    if firma_id is not None:
        kosullar.append(Fatura.firma_id == firma_id)
    if vadesi_gecmis:
        kosullar += [
            Fatura.durum == "kesildi",
            Fatura.vade_tarihi < is_gunu(),
            Fatura.odenen_tutar < Fatura.genel_toplam,
        ]
    if arama:
        kalip = f"%{arama}%"
        kosullar.append(or_(Fatura.kod.ilike(kalip), Firma.ad.ilike(kalip)))
    # Tek varlık değil (Fatura, firma adı) satırı: sıralama yardımcısının tip sınırına uydur.
    sorgu = cast(
        "Select[Any]",
        select(Fatura, Firma.ad).join(Firma, Firma.id == Fatura.firma_id).where(*kosullar),
    )
    toplam = await db.scalar(
        select(func.count())
        .select_from(Fatura)
        .join(Firma, Firma.id == Fatura.firma_id)
        .where(*kosullar)
    )
    sorgu = siralama_uygula(
        sorgu,
        siralama=siralama,
        yon=yon,
        izinli=_FATURA_SIRALAMA,
        varsayilan=Fatura.id,
        varsayilan_yon="desc",
    )
    satirlar = (await db.execute(sorgu.offset((sayfa - 1) * adet).limit(adet))).all()
    return sayfali(
        [_fatura_cevap(f, ad) for f, ad in satirlar],
        sayfa=sayfa,
        adet=adet,
        toplam=int(toplam or 0),
    )


@router.post(
    "/faturalar", response_model=Zarf[FaturaCevapDTO], status_code=201, summary="Fatura hazırla"
)
async def fatura_olustur(
    govde: FaturaOlusturDTO, k: Yaz, db: Oturum, _t: TenantDep
) -> dict[str, Any]:
    f = await service.fatura_olustur(
        db,
        tur=govde.tur,
        firma_id=govde.firma_id,
        fatura_tarihi=govde.fatura_tarihi,
        vade_gun=govde.vade_gun,
        kalemler=_kalemler(govde.kalemler),
        aciklama=govde.aciklama,
        senaryo=govde.senaryo,
        satinalma_siparisi_id=govde.satinalma_siparisi_id,
        kullanici=k,
    )
    await denetim_yaz(db, eylem="olustur", kaynak="fatura", kaynak_id=str(f.id), kullanici=k)
    return await _fatura_yanit(db, f, "Fatura taslağı oluşturuldu")


@router.get("/faturalar/{fatura_id}", response_model=Zarf[FaturaCevapDTO], summary="Fatura detayı")
async def fatura_detay(fatura_id: int, _k: Oku, db: Oturum, _t: TenantDep) -> dict[str, Any]:
    return await _fatura_yanit(db, await _fatura_getir(db, fatura_id), "Fatura")


@router.patch(
    "/faturalar/{fatura_id}", response_model=Zarf[FaturaCevapDTO], summary="Taslak faturayı düzenle"
)
async def fatura_guncelle(
    fatura_id: int, govde: FaturaGuncelleDTO, k: Yaz, db: Oturum, _t: TenantDep
) -> dict[str, Any]:
    f = await service.fatura_kilitle(db, fatura_id)
    await service.fatura_guncelle(
        db,
        f,
        firma_id=govde.firma_id,
        fatura_tarihi=govde.fatura_tarihi,
        vade_gun=govde.vade_gun,
        kalemler=_kalemler(govde.kalemler) if govde.kalemler is not None else None,
        aciklama=govde.aciklama,
    )
    await denetim_yaz(db, eylem="guncelle", kaynak="fatura", kaynak_id=str(f.id), kullanici=k)
    return await _fatura_yanit(db, f, "Fatura güncellendi")


@router.post(
    "/faturalar/{fatura_id}/gonder", response_model=Zarf[FaturaCevapDTO], summary="Onaya gönder"
)
async def fatura_gonder(fatura_id: int, k: Yaz, db: Oturum, _t: TenantDep) -> dict[str, Any]:
    f = await service.fatura_gonder(db, await service.fatura_kilitle(db, fatura_id))
    await denetim_yaz(db, eylem="gonder", kaynak="fatura", kaynak_id=str(f.id), kullanici=k)
    return await _fatura_yanit(db, f, "Fatura onaya gönderildi")


@router.post(
    "/faturalar/{fatura_id}/kes", response_model=Zarf[FaturaCevapDTO], summary="Faturayı kes"
)
async def fatura_kes(fatura_id: int, k: Onay, db: Oturum, _t: TenantDep) -> dict[str, Any]:
    f = await service.fatura_kes(db, await service.fatura_kilitle(db, fatura_id), kesen=k)
    await denetim_yaz(db, eylem="kes", kaynak="fatura", kaynak_id=str(f.id), kullanici=k)
    return await _fatura_yanit(db, f, "Fatura kesildi ve cariye işlendi")


@router.post(
    "/faturalar/{fatura_id}/iade",
    response_model=Zarf[FaturaCevapDTO],
    summary="Faturayı düzeltmeye iade et",
)
async def fatura_iade(
    fatura_id: int, govde: NedenDTO, k: Onay, db: Oturum, _t: TenantDep
) -> dict[str, Any]:
    f = await service.fatura_iade(
        db, await service.fatura_kilitle(db, fatura_id), neden=govde.neden
    )
    await denetim_yaz(
        db,
        eylem="iade",
        kaynak="fatura",
        kaynak_id=str(f.id),
        kullanici=k,
        detay={"neden": govde.neden},
    )
    return await _fatura_yanit(db, f, "Fatura düzeltmeye iade edildi")


@router.post(
    "/faturalar/{fatura_id}/iptal", response_model=Zarf[FaturaCevapDTO], summary="Faturayı iptal et"
)
async def fatura_iptal(
    fatura_id: int, govde: NedenDTO, k: Onay, db: Oturum, _t: TenantDep
) -> dict[str, Any]:
    f = await service.fatura_iptal(
        db, await service.fatura_kilitle(db, fatura_id), neden=govde.neden, kullanici=k
    )
    await denetim_yaz(
        db,
        eylem="iptal",
        kaynak="fatura",
        kaynak_id=str(f.id),
        kullanici=k,
        detay={"neden": govde.neden},
    )
    return await _fatura_yanit(db, f, "Fatura iptal edildi")


@router.get("/faturalar/{fatura_id}/pdf", summary="Fatura PDF'i (bilgi nüshası)")
async def fatura_pdf_indir(fatura_id: int, k: Oku, db: Oturum, tenant: TenantDep) -> Response:
    f = await _fatura_getir(db, fatura_id)
    await db.refresh(f, ["kalemler"])
    firma = await db.get(Firma, f.firma_id)
    karsi = PdfFirma(
        ad=firma.ad if firma else "—",
        vergi_dairesi=firma.vergi_dairesi if firma else "",
        vergi_no=firma.vergi_no if firma else "",
        adres=firma.adres if firma else "",
        il=firma.il if firma else "",
        telefon=firma.telefon if firma else "",
        eposta=firma.eposta if firma else "",
    )
    biz = PdfFirma(ad=tenant.ad)
    icerik = fatura_pdf(
        kod=f.kod,
        tur=f.tur,
        durum=f.durum,
        fatura_tarihi=f.fatura_tarihi,
        vade_tarihi=f.vade_tarihi,
        para_birimi=f.para_birimi,
        ettn=str(f.ettn),
        aciklama=f.aciklama,
        satici=biz if f.tur == "satis" else karsi,
        alici=karsi if f.tur == "satis" else biz,
        kalemler=[
            FaturaPdfKalem(
                aciklama=x.aciklama,
                miktar=x.miktar,
                birim=x.birim,
                birim_fiyat=x.birim_fiyat,
                kdv_orani=x.kdv_orani,
                satir_tutari=x.satir_tutari,
                kdv_tutari=x.kdv_tutari,
            )
            for x in f.kalemler
        ],
        ara_toplam=f.ara_toplam,
        kdv_toplam=f.kdv_toplam,
        genel_toplam=f.genel_toplam,
        odenen=f.odenen_tutar,
    )
    await denetim_yaz(db, eylem="disa_aktar", kaynak="fatura", kaynak_id=str(f.id), kullanici=k)
    return Response(
        content=icerik,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{f.kod}.pdf"'},
    )


# ── Tahsilat / ödeme ─────────────────────────────────────────────────────────


def _odeme_cevap(o: Odeme, firma_ad: str, fatura_kod: str | None) -> dict[str, Any]:
    return OdemeCevapDTO(
        id=o.id,
        kod=o.kod,
        tur=o.tur,
        firma_id=o.firma_id,
        firma_ad=firma_ad,
        fatura_id=o.fatura_id,
        fatura_kod=fatura_kod,
        tarih=o.tarih,
        tutar=_f(o.tutar),
        yontem=o.yontem,
        aciklama=o.aciklama,
        olusturma_tarihi=o.olusturma_tarihi,
    ).model_dump()


@router.get("/odemeler", response_model=Zarf[list[OdemeCevapDTO]], summary="Tahsilat ve ödemeler")
async def odeme_listele(
    _k: Oku,
    db: Oturum,
    _t: TenantDep,
    sayfa: int = 1,
    adet: int = 20,
    tur: str | None = None,
    firma_id: int | None = None,
    arama: str | None = None,
) -> dict[str, Any]:
    sayfa, adet = max(sayfa, 1), min(max(adet, 1), 100)
    kosullar: list[Any] = []
    if tur:
        kosullar.append(Odeme.tur == tur)
    if firma_id is not None:
        kosullar.append(Odeme.firma_id == firma_id)
    if arama:
        kalip = f"%{arama}%"
        kosullar.append(or_(Odeme.kod.ilike(kalip), Firma.ad.ilike(kalip)))
    taban = (
        select(Odeme, Firma.ad, Fatura.kod)
        .join(Firma, Firma.id == Odeme.firma_id)
        .outerjoin(Fatura, Fatura.id == Odeme.fatura_id)
        .where(*kosullar)
    )
    toplam = await db.scalar(
        select(func.count())
        .select_from(Odeme)
        .join(Firma, Firma.id == Odeme.firma_id)
        .where(*kosullar)
    )
    satirlar = (
        await db.execute(
            taban.order_by(Odeme.tarih.desc(), Odeme.id.desc())
            .offset((sayfa - 1) * adet)
            .limit(adet)
        )
    ).all()
    return sayfali(
        [_odeme_cevap(o, ad, fk) for o, ad, fk in satirlar],
        sayfa=sayfa,
        adet=adet,
        toplam=int(toplam or 0),
    )


@router.post(
    "/odemeler",
    response_model=Zarf[OdemeCevapDTO],
    status_code=201,
    summary="Tahsilat ya da ödeme kaydet",
)
async def odeme_olustur(
    govde: OdemeOlusturDTO,
    k: Yaz,
    db: Oturum,
    _t: TenantDep,
    response: Response,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=80)] = None,
) -> dict[str, Any]:
    if govde.tur == "odeme" and not k.izin_var("finans:onay"):
        raise YetkiHatasi("Firmaya ödeme kaydı finans onay yetkisi ister (finans:onay)")
    odeme, yeni = await service.odeme_kaydet(
        db,
        tur=govde.tur,
        firma_id=govde.firma_id,
        tutar=govde.tutar,
        tarih=govde.tarih,
        yontem=govde.yontem,
        fatura_id=govde.fatura_id,
        aciklama=govde.aciklama,
        idempotency_anahtari=idempotency_key,
        kullanici=k,
    )
    if yeni:
        await denetim_yaz(db, eylem="olustur", kaynak="odeme", kaynak_id=str(odeme.id), kullanici=k)
    else:
        response.status_code = 200  # aynı Idempotency-Key: ilk kayıt döner, ikinci ödeme açılmaz
    fatura_kod = (
        await db.scalar(select(Fatura.kod).where(Fatura.id == odeme.fatura_id))
        if odeme.fatura_id
        else None
    )
    return basari(
        _odeme_cevap(odeme, await _firma_ad(db, odeme.firma_id), fatura_kod),
        mesaj="Kaydedildi" if yeni else "Bu istek daha önce işlenmişti",
    )


# ── Cari ─────────────────────────────────────────────────────────────────────


@router.get("/cari-hesaplar", response_model=Zarf[list[CariHesapCevapDTO]], summary="Cari hesaplar")
async def cari_listele(
    _k: Oku,
    db: Oturum,
    _t: TenantDep,
    sayfa: int = 1,
    adet: int = 20,
    arama: str | None = None,
    bakiyeli: bool = False,
) -> dict[str, Any]:
    sayfa, adet = max(sayfa, 1), min(max(adet, 1), 100)
    bugun = is_gunu()
    acik = Fatura.genel_toplam - Fatura.odenen_tutar
    fatura_ozet = (
        select(
            Fatura.firma_id.label("firma_id"),
            func.count().label("acik_fatura"),
            func.coalesce(
                func.sum(acik).filter(Fatura.vade_tarihi < bugun, Fatura.tur == "satis"), 0
            ).label("vadesi_gecen"),
        )
        .where(Fatura.durum == "kesildi")
        .group_by(Fatura.firma_id)
        .subquery()
    )
    son = (
        select(CariHareket.cari_id, func.max(CariHareket.tarih).label("son"))
        .group_by(CariHareket.cari_id)
        .subquery()
    )
    kosullar: list[Any] = []
    if arama:
        kosullar.append(Firma.ad.ilike(f"%{arama}%"))
    if bakiyeli:
        kosullar.append(CariHesap.bakiye != 0)
    sorgu = (
        select(
            CariHesap,
            Firma.ad,
            Firma.tip,
            func.coalesce(fatura_ozet.c.acik_fatura, 0),
            func.coalesce(fatura_ozet.c.vadesi_gecen, 0),
            son.c.son,
        )
        .join(Firma, Firma.id == CariHesap.firma_id)
        .outerjoin(fatura_ozet, fatura_ozet.c.firma_id == CariHesap.firma_id)
        .outerjoin(son, son.c.cari_id == CariHesap.id)
        .where(*kosullar)
    )
    toplam = await db.scalar(
        select(func.count())
        .select_from(CariHesap)
        .join(Firma, Firma.id == CariHesap.firma_id)
        .where(*kosullar)
    )
    satirlar = (
        await db.execute(
            sorgu.order_by(func.abs(CariHesap.bakiye).desc(), Firma.ad)
            .offset((sayfa - 1) * adet)
            .limit(adet)
        )
    ).all()
    return sayfali(
        [
            CariHesapCevapDTO(
                firma_id=c.firma_id,
                firma_ad=ad,
                firma_tip=tip,
                bakiye=_f(c.bakiye),
                para_birimi=c.para_birimi,
                acik_fatura=int(af),
                vadesi_gecen=float(vg),
                son_hareket=sh,
            ).model_dump()
            for c, ad, tip, af, vg, sh in satirlar
        ],
        sayfa=sayfa,
        adet=adet,
        toplam=int(toplam or 0),
    )


@router.get(
    "/cari-hesaplar/{firma_id}/ekstre",
    response_model=Zarf[CariEkstreDTO],
    summary="Cari hesap ekstresi",
)
async def cari_ekstre(
    firma_id: int,
    _k: Oku,
    db: Oturum,
    _t: TenantDep,
    baslangic: date | None = None,
    bitis: date | None = None,
) -> dict[str, Any]:
    firma = await db.get(Firma, firma_id)
    if firma is None:
        raise KaynakBulunamadi("Firma bulunamadı")
    cari = await db.scalar(select(CariHesap).where(CariHesap.firma_id == firma_id))
    bitis = bitis or is_gunu()
    baslangic = baslangic or (bitis - timedelta(days=365))
    hareketler: list[CariHareket] = []
    acilis = Decimal("0.00")
    if cari is not None:
        acilis = Decimal(
            await db.scalar(
                select(func.coalesce(func.sum(CariHareket.tutar), 0)).where(
                    CariHareket.cari_id == cari.id, CariHareket.tarih < baslangic
                )
            )
            or 0
        )
        hareketler = list(
            (
                await db.execute(
                    select(CariHareket)
                    .where(
                        CariHareket.cari_id == cari.id,
                        CariHareket.tarih >= baslangic,
                        CariHareket.tarih <= bitis,
                    )
                    .order_by(CariHareket.tarih, CariHareket.id)
                )
            ).scalars()
        )
    # Ekstre tarihe göre sıralı yürüyen bakiye gösterir (kayıt anındaki bakiye_sonrasi geriye
    # tarihli hareketlerde ekstre sırasıyla uyuşmayabilir).
    yuruyen = acilis
    satirlar = []
    for h in hareketler:
        yuruyen += h.tutar
        satirlar.append(
            CariHareketCevapDTO(
                id=h.id,
                tarih=h.tarih,
                tur=h.tur,
                aciklama=h.aciklama,
                borc=_f(h.tutar) if h.tutar > 0 else 0.0,
                alacak=_f(-h.tutar) if h.tutar < 0 else 0.0,
                bakiye_sonrasi=_f(yuruyen),
                kaynak=h.kaynak,
            )
        )
    return basari(
        CariEkstreDTO(
            firma_id=firma_id,
            firma_ad=firma.ad,
            bakiye=_f(cari.bakiye if cari else None),
            acilis_bakiyesi=_f(acilis),
            hareketler=satirlar,
        ).model_dump(),
        mesaj="Cari ekstre",
    )


# ── Özet ve raporlar ─────────────────────────────────────────────────────────


@router.get("/finans/ozet", response_model=Zarf[FinansOzetDTO], summary="Finans özeti")
async def finans_ozet(_k: Oku, db: Oturum, _t: TenantDep) -> dict[str, Any]:
    o = await service.ozet(db, is_gunu())
    return basari(
        FinansOzetDTO(
            **{a: (float(v) if isinstance(v, Decimal) else v) for a, v in o.items()}
        ).model_dump(),
        mesaj="Finans özeti",
    )


def _yon(veri: dict[str, Any]) -> YaslandirmaYonuDTO:
    def kovalar(d: dict[str, Any]) -> dict[str, float]:
        return {
            "vadesi_gelmemis": _f(d["vadesi_gelmemis"]),
            "gun_0_30": _f(d["0_30"]),
            "gun_31_60": _f(d["31_60"]),
            "gun_61_90": _f(d["61_90"]),
            "gun_90_ustu": _f(d["90_ustu"]),
        }

    return YaslandirmaYonuDTO(
        toplam=_f(veri["toplam"]),
        **kovalar(veri["kovalar"]),
        firmalar=[
            YaslandirmaFirmaDTO(
                firma_id=x["firma_id"], firma_ad=x["firma_ad"], toplam=_f(x["toplam"]), **kovalar(x)
            )
            for x in veri["firmalar"]
        ],
    )


@router.get(
    "/finans/yaslandirma", response_model=Zarf[YaslandirmaDTO], summary="Alacak/borç yaşlandırma"
)
async def finans_yaslandirma(_k: Oku, db: Oturum, _t: TenantDep) -> dict[str, Any]:
    v = await service.yaslandirma(db, is_gunu())
    return basari(
        YaslandirmaDTO(alacak=_yon(v["alacak"]), borc=_yon(v["borc"])).model_dump(),
        mesaj="Yaşlandırma",
    )


@router.get(
    "/finans/maliyet",
    response_model=Zarf[list[IsEmriMaliyetiDTO]],
    summary="Üretim malzeme maliyeti (kapanan iş emirleri)",
)
async def finans_maliyet(_k: Oku, db: Oturum, _t: TenantDep, gun: int = 30) -> dict[str, Any]:
    gun = min(max(gun, 1), 366)
    bitis = datetime.now(UTC)
    kayitlar = await maliyet.uretim_maliyeti(db, baslangic=bitis - timedelta(days=gun), bitis=bitis)
    return basari(
        [
            IsEmriMaliyetiDTO(
                is_emri_id=m.is_emri_id,
                is_emri_kod=m.is_emri_kod,
                urun_kod=m.urun_kod,
                urun_ad=m.urun_ad,
                miktar=float(m.miktar) if m.miktar is not None else None,
                kapanis_tarihi=m.kapanis_tarihi,
                malzeme_maliyeti=_f(m.malzeme_maliyeti),
                birim_maliyet=float(m.birim_maliyet) if m.birim_maliyet is not None else None,
                eksik_fiyat=m.eksik_fiyat,
                kalemler=[
                    MaliyetKalemiDTO(
                        malzeme_id=x.malzeme_id,
                        malzeme_kod=x.malzeme_kod,
                        malzeme_ad=x.malzeme_ad,
                        miktar=float(x.miktar),
                        birim_fiyat=float(x.birim_fiyat) if x.birim_fiyat is not None else None,
                        fiyat_kaynagi=x.fiyat_kaynagi,
                        tutar=float(x.tutar) if x.tutar is not None else None,
                    )
                    for x in m.kalemler
                ],
            ).model_dump()
            for m in kayitlar
        ],
        mesaj="Üretim maliyeti",
    )


@router.put(
    "/faturalar/{fatura_id}/gib-durumu",
    response_model=Zarf[FaturaCevapDTO],
    summary="e-Fatura iletim durumunu işle (entegratörden dönen sonuç)",
)
async def fatura_gib_durumu(
    fatura_id: int, govde: GibDurumDTO, k: Onay, db: Oturum, _t: TenantDep
) -> dict[str, Any]:
    f = await service.fatura_kilitle(db, fatura_id)
    if f.durum not in ("kesildi", "kapandi"):
        raise CakismaHatasi("Yalnız kesilmiş faturanın e-Fatura durumu işlenir")
    onceki, f.gib_durumu = f.gib_durumu, govde.gib_durumu
    await denetim_yaz(
        db,
        eylem="gib_durumu",
        kaynak="fatura",
        kaynak_id=str(f.id),
        kullanici=k,
        detay={"onceki": onceki, "yeni": govde.gib_durumu},
    )
    return await _fatura_yanit(db, f, "e-Fatura durumu işlendi")


# ── e-Fatura entegratörü (API anahtarı, salt okunur) ─────────────────────────

entegrator_router = APIRouter(
    prefix="/entegrasyon",
    tags=["Entegrasyon"],
    dependencies=[Depends(modul_gerekli("entegrasyon")), Depends(modul_gerekli("finans"))],
)


@entegrator_router.get(
    "/faturalar",
    response_model=Zarf[list[EFaturaDisDTO]],
    summary="Kesilmiş faturalar (API anahtarı; kapsam finans:oku) — e-Fatura entegratörü için",
)
async def efatura_listele(
    _anahtar: Annotated[ApiAnahtari, Depends(api_izin_gerekli("finans:oku"))],
    db: Oturum,
    tenant: TenantDep,
    gib_durumu: str | None = "gonderilmedi",
    sayfa: int = 1,
    adet: int = 100,
) -> dict[str, Any]:
    sayfa, adet = max(sayfa, 1), min(max(adet, 1), 500)
    kosullar: list[Any] = [Fatura.durum.in_(("kesildi", "kapandi"))]
    if gib_durumu:
        kosullar.append(Fatura.gib_durumu == gib_durumu)
    toplam = await db.scalar(select(func.count()).select_from(Fatura).where(*kosullar))
    satirlar = (
        await db.execute(
            select(Fatura, Firma)
            .join(Firma, Firma.id == Fatura.firma_id)
            .where(*kosullar)
            .order_by(Fatura.kesim_tarihi, Fatura.id)
            .offset((sayfa - 1) * adet)
            .limit(adet)
        )
    ).all()
    kayitlar = []
    for f, firma in satirlar:
        await db.refresh(f, ["kalemler"])
        kayitlar.append(
            EFaturaDisDTO(
                ettn=str(f.ettn),
                kod=f.kod,
                tur=f.tur,
                senaryo=f.senaryo,
                fatura_tarihi=f.fatura_tarihi,
                para_birimi=f.para_birimi,
                gonderen=tenant.ad if f.tur == "satis" else firma.ad,
                karsi_taraf_unvan=firma.ad,
                karsi_taraf_vkn=firma.vergi_no,
                karsi_taraf_vergi_dairesi=firma.vergi_dairesi,
                ara_toplam=_f(f.ara_toplam),
                kdv_toplam=_f(f.kdv_toplam),
                genel_toplam=_f(f.genel_toplam),
                gib_durumu=f.gib_durumu,
                kalemler=[
                    FaturaKalemiCevapDTO(
                        id=x.id,
                        sira=x.sira,
                        aciklama=x.aciklama,
                        malzeme_id=x.malzeme_id,
                        miktar=float(x.miktar),
                        birim=x.birim,
                        birim_fiyat=float(x.birim_fiyat),
                        kdv_orani=x.kdv_orani,
                        satir_tutari=_f(x.satir_tutari),
                        kdv_tutari=_f(x.kdv_tutari),
                    )
                    for x in f.kalemler
                ],
            ).model_dump()
        )
    return sayfali(kayitlar, sayfa=sayfa, adet=adet, toplam=int(toplam or 0))
