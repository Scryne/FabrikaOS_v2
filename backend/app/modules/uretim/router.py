"""Üretim modülü uçları (``/api/v1``).

Tüm uçlar tenant-kapsamlı ve RBAC korumalı (``uretim:oku`` / ``uretim:yaz``).
Yazma işlemleri denetim izine kaydedilir.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.olaylar import olay_yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.uretim import repository, service
from app.modules.uretim.models import MAKINE_DURUMLARI, ArizaKaydi, Makine, UretimVerisi
from app.modules.uretim.schemas import (
    DurumSayiDTO,
    MakineCevapDTO,
    MakineDurumDTO,
    MakineGuncelleDTO,
    MakineOlusturDTO,
    OeeCevapDTO,
    OeeOzetSatirDTO,
    UretimGirisDTO,
    UretimOzetDTO,
    UretimVerisiCevapDTO,
)

router = APIRouter(tags=["Üretim"], dependencies=[Depends(modul_gerekli("uretim"))])


def _makine_cevap(m: Makine) -> dict[str, Any]:
    return MakineCevapDTO(
        id=m.id,
        kod=m.kod,
        ad=m.ad,
        durum=m.durum,
        oee_hedefi=m.oee_hedefi,
        enlem=m.enlem,
        boylam=m.boylam,
    ).model_dump()


def _uretim_cevap(u: UretimVerisi) -> dict[str, Any]:
    return UretimVerisiCevapDTO(
        id=u.id,
        makine_id=u.makine_id,
        zaman=u.zaman,
        vardiya=u.vardiya,
        planlanan_sure_dk=u.planlanan_sure_dk,
        durus_sure_dk=u.durus_sure_dk,
        toplam_adet=u.toplam_adet,
        saglam_adet=u.saglam_adet,
        ideal_cevrim_sn=u.ideal_cevrim_sn,
        lot_no=u.lot_no,
    ).model_dump()


# --- Makineler ---
@router.post(
    "/makineler", response_model=Zarf[MakineCevapDTO], status_code=201, summary="Makine oluştur"
)
async def makine_olustur(
    govde: MakineOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    if await repository.makine_kod_var_mi(db, govde.kod):
        raise CakismaHatasi("Bu kod ile makine zaten var")
    makine = await repository.makine_ekle(
        db,
        Makine(
            kod=govde.kod,
            ad=govde.ad,
            oee_hedefi=govde.oee_hedefi,
            enlem=govde.enlem,
            boylam=govde.boylam,
        ),
    )
    await denetim_yaz(
        db, eylem="olustur", kaynak="makine", kaynak_id=str(makine.id), kullanici=kullanici
    )
    return basari(_makine_cevap(makine), mesaj="Makine oluşturuldu")


@router.get("/makineler", response_model=Zarf[list[MakineCevapDTO]], summary="Makineleri listele")
async def makine_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
    durum: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.makine_listele(
        db, sayfa=sayfa, adet=adet, durum=durum, arama=arama, siralama=siralama, yon=yon
    )
    return sayfali([_makine_cevap(m) for m in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/makineler/{makine_id}", response_model=Zarf[MakineCevapDTO], summary="Makine detayı")
async def makine_detay(
    makine_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    makine = await repository.makine_getir(db, makine_id)
    if makine is None:
        raise KaynakBulunamadi("Makine bulunamadı")
    return basari(_makine_cevap(makine), mesaj="Makine detayı")


@router.patch(
    "/makineler/{makine_id}",
    response_model=Zarf[MakineCevapDTO],
    summary="Makine bilgilerini güncelle (ad/OEE hedefi/koordinat)",
)
async def makine_guncelle(
    makine_id: int,
    govde: MakineGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    makine = await repository.makine_getir(db, makine_id)
    if makine is None:
        raise KaynakBulunamadi("Makine bulunamadı")
    degisen = govde.model_dump(exclude_unset=True)
    for alan, deger in degisen.items():
        setattr(makine, alan, deger)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="guncelle",
        kaynak="makine",
        kaynak_id=str(makine.id),
        kullanici=kullanici,
        detay={"alanlar": sorted(degisen)},
    )
    return basari(_makine_cevap(makine), mesaj="Makine güncellendi")


@router.patch(
    "/makineler/{makine_id}/durum",
    response_model=Zarf[MakineCevapDTO],
    summary="Makine durumunu güncelle",
)
async def makine_durum_guncelle(
    makine_id: int,
    govde: MakineDurumDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if govde.durum not in MAKINE_DURUMLARI:
        raise DogrulamaHatasi(
            "Geçersiz durum",
            detaylar=[
                {"alan": "durum", "mesaj": f"Geçerli: {', '.join(sorted(MAKINE_DURUMLARI))}"}
            ],
        )
    makine = await repository.makine_getir(db, makine_id)
    if makine is None:
        raise KaynakBulunamadi("Makine bulunamadı")
    onceki_durum = makine.durum
    makine.durum = govde.durum
    # Kenar-tetikli `ariza.olustu` (S18): yalnız arızaya GEÇİŞTE bir kez — durum
    # değişikliğiyle aynı transaction'da outbox'a yazılır (webhook relay teslim eder).
    if govde.durum == "ariza" and onceki_durum != "ariza":
        # Arıza kaydı otomasyonu (S24): geçişle birlikte açık ArizaKaydi açılır —
        # MTBF/MTTR metriklerinin veri kaynağı.
        db.add(ArizaKaydi(makine_id=makine.id, baslangic=datetime.now(UTC), tur="ariza"))
        await olay_yayinla(
            db,
            olay_turu="ariza.olustu",
            govde={
                "makine_id": makine.id,
                "makine_kod": makine.kod,
                "makine_ad": makine.ad,
                "onceki_durum": onceki_durum,
            },
        )
    if onceki_durum == "ariza" and govde.durum != "ariza":
        # Arızadan çıkış: açık kayıt kapanır (onarım süresi = MTTR girdisi).
        acik_kayitlar = (
            (
                await db.execute(
                    select(ArizaKaydi).where(
                        ArizaKaydi.makine_id == makine.id, ArizaKaydi.bitis.is_(None)
                    )
                )
            )
            .scalars()
            .all()
        )
        for kayit in acik_kayitlar:
            kayit.bitis = datetime.now(UTC)
            kayit.cozuldu = True
    await denetim_yaz(
        db,
        eylem="durum_guncelle",
        kaynak="makine",
        kaynak_id=str(makine.id),
        kullanici=kullanici,
        detay={"durum": govde.durum},
    )
    await yayinla(
        tenant.slug,
        {"tur": "makine.durum", "makine_id": makine.id, "durum": makine.durum},
    )
    return basari(_makine_cevap(makine), mesaj="Durum güncellendi")


@router.get("/makineler/{makine_id}/oee", response_model=Zarf[OeeCevapDTO], summary="Makine OEE")
async def makine_oee(
    makine_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    baslangic: Annotated[datetime | None, Query()] = None,
    bitis: Annotated[datetime | None, Query()] = None,
    vardiya: Annotated[str | None, Query(max_length=20)] = None,
) -> dict[str, Any]:
    makine = await repository.makine_getir(db, makine_id)
    if makine is None:
        raise KaynakBulunamadi("Makine bulunamadı")
    sonuc, sayi = await service.makine_oee(
        db, makine_id, baslangic=baslangic, bitis=bitis, vardiya=vardiya
    )
    veri = OeeCevapDTO(
        makine_id=makine_id,
        kullanilabilirlik=sonuc.kullanilabilirlik,
        performans=sonuc.performans,
        kalite=sonuc.kalite,
        oee=sonuc.oee,
        kayit_sayisi=sayi,
    )
    return basari(veri.model_dump(), mesaj="OEE hesaplandı")


# --- Üretim verileri ---
@router.post(
    "/uretim-verileri",
    response_model=Zarf[UretimVerisiCevapDTO],
    status_code=201,
    summary="Üretim verisi girişi",
)
async def uretim_girisi(
    govde: UretimGirisDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if govde.saglam_adet > govde.toplam_adet:
        raise DogrulamaHatasi(
            "Sağlam adet toplam adetten büyük olamaz",
            detaylar=[{"alan": "saglam_adet", "mesaj": "toplam_adet'i aşamaz"}],
        )
    if await repository.makine_getir(db, govde.makine_id) is None:
        raise KaynakBulunamadi("Makine bulunamadı")

    kayit = await repository.uretim_ekle(
        db,
        UretimVerisi(
            makine_id=govde.makine_id,
            zaman=govde.zaman or datetime.now(UTC),
            vardiya=govde.vardiya,
            planlanan_sure_dk=govde.planlanan_sure_dk,
            durus_sure_dk=govde.durus_sure_dk,
            toplam_adet=govde.toplam_adet,
            saglam_adet=govde.saglam_adet,
            ideal_cevrim_sn=govde.ideal_cevrim_sn,
            lot_no=govde.lot_no,
        ),
    )
    await denetim_yaz(
        db, eylem="olustur", kaynak="uretim_verisi", kaynak_id=str(kayit.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "uretim.eklendi", "makine_id": kayit.makine_id})
    return basari(_uretim_cevap(kayit), mesaj="Üretim verisi kaydedildi")


@router.get(
    "/uretim-verileri",
    response_model=Zarf[list[UretimVerisiCevapDTO]],
    summary="Üretim verilerini listele",
)
async def uretim_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
    makine_id: int | None = None,
    baslangic: Annotated[datetime | None, Query()] = None,
    bitis: Annotated[datetime | None, Query()] = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.uretim_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        makine_id=makine_id,
        baslangic=baslangic,
        bitis=bitis,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_uretim_cevap(u) for u in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/oee/ozet", response_model=Zarf[list[OeeOzetSatirDTO]], summary="Makine bazlı OEE özeti"
)
async def oee_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    baslangic: Annotated[datetime | None, Query()] = None,
    bitis: Annotated[datetime | None, Query()] = None,
    vardiya: Annotated[str | None, Query(max_length=20)] = None,
) -> dict[str, Any]:
    satirlar = await service.oee_ozet(db, baslangic=baslangic, bitis=bitis, vardiya=vardiya)
    veri = [
        OeeOzetSatirDTO(
            makine_id=mid,
            makine_kod=kod,
            kullanilabilirlik=s.kullanilabilirlik,
            performans=s.performans,
            kalite=s.kalite,
            oee=s.oee,
            kayit_sayisi=sayi,
        ).model_dump()
        for mid, kod, s, sayi in satirlar
    ]
    return basari(veri, mesaj="OEE özeti")


@router.post(
    "/oee/dusuk-tara",
    response_model=Zarf[dict[str, int]],
    summary="Düşük OEE taraması (kenar-tetikli oee.dustu olayı; makine+gün başına bir kez)",
)
async def oee_dusuk_tara(
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    esik: Annotated[float, Query(gt=0, le=1)] = 0.6,
) -> dict[str, Any]:
    """Bugünkü OEE'si hedefin (``makine.oee_hedefi``, yoksa ``esik``) altındaki makineler
    için ``oee.dustu`` outbox olayı yazar — S12 ``yaklasan-tara`` deseni (webhook S18)."""
    islenen = await service.dusuk_oee_tara(db, tenant_slug=tenant.slug, esik=esik)
    await denetim_yaz(
        db,
        eylem="dusuk_oee_tara",
        kaynak="makine",
        kaynak_id="-",
        kullanici=kullanici,
        detay={"esik": esik, "islenen": islenen},
    )
    return basari({"islenen": islenen}, mesaj=f"{islenen} makine için oee.dustu üretildi")


@router.get("/uretim/ozet", response_model=Zarf[UretimOzetDTO], summary="Üretim özeti (pano/KPI)")
async def uretim_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    toplam = await db.scalar(select(func.count()).select_from(Makine)) or 0

    durum_sonuc = await db.execute(select(Makine.durum, func.count()).group_by(Makine.durum))
    sayac: dict[str, int] = dict.fromkeys(MAKINE_DURUMLARI, 0)
    for durum, adet in durum_sonuc.all():
        sayac[durum] = int(adet)

    ozet_satirlar = await service.oee_ozet(db)
    uretimli = len(ozet_satirlar)
    ort_oee = sum(s.oee for _mid, _kod, s, _sayi in ozet_satirlar) / uretimli if uretimli else 0.0

    ozet = UretimOzetDTO(
        toplam_makine=int(toplam),
        calisan=sayac.get("calisiyor", 0),
        durdu=sayac.get("durdu", 0),
        bakimda=sayac.get("bakimda", 0),
        arizali=sayac.get("ariza", 0),
        uretimli_makine=uretimli,
        ortalama_oee=ort_oee,
        durum_dagilimi=[DurumSayiDTO(durum=d, adet=sayac[d]) for d in MAKINE_DURUMLARI],
    )
    return basari(ozet.model_dump(), mesaj="Üretim özeti")


# --- İzlenebilirlik (S24) ---
class IzlenebilirlikIsEmriDTO(BaseModel):
    id: int
    kod: str
    durum: str
    urun_id: int | None = None
    miktar: float | None = None
    kapanis_tarihi: datetime | None = None


class IzlenebilirlikUretimDTO(BaseModel):
    makine_id: int
    makine_kod: str
    kayit_sayisi: int
    toplam_adet: int
    saglam_adet: int
    ilk_zaman: datetime | None = None
    son_zaman: datetime | None = None


class IzlenebilirlikTuketimDTO(BaseModel):
    malzeme_id: int
    malzeme_kod: str
    malzeme_ad: str
    miktar: float
    is_emri_kod: str


class IzlenebilirlikCevapDTO(BaseModel):
    """Lot ileri/geri izleme zinciri: iş emirleri + üretim kayıtları + tüketilen malzemeler."""

    lot_no: str
    is_emirleri: list[IzlenebilirlikIsEmriDTO]
    uretim: list[IzlenebilirlikUretimDTO]
    tuketilen_malzemeler: list[IzlenebilirlikTuketimDTO]


@router.get(
    "/izlenebilirlik",
    response_model=Zarf[IzlenebilirlikCevapDTO],
    summary="Lot izlenebilirliği (ileri/geri zincir)",
)
async def izlenebilirlik(
    lot: Annotated[str, Query(min_length=1, max_length=50)],
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    """Lot numarasından zinciri kurar: hangi iş emirleri üretti (→ ürün + BOM tüketimi
    = **geri izleme**), hangi makineler ne zaman üretim kaydı yazdı (= **ileri izleme**)."""
    from app.modules.isemri.models import IsEmri
    from app.modules.stok.models import Malzeme, StokHareketi

    is_emirleri = (
        (await db.execute(select(IsEmri).where(IsEmri.lot_no == lot).order_by(IsEmri.id)))
        .scalars()
        .all()
    )

    uretim_satirlari = (
        await db.execute(
            select(
                UretimVerisi.makine_id,
                Makine.kod,
                func.count(),
                func.coalesce(func.sum(UretimVerisi.toplam_adet), 0),
                func.coalesce(func.sum(UretimVerisi.saglam_adet), 0),
                func.min(UretimVerisi.zaman),
                func.max(UretimVerisi.zaman),
            )
            .join(Makine, Makine.id == UretimVerisi.makine_id)
            .where(UretimVerisi.lot_no == lot)
            .group_by(UretimVerisi.makine_id, Makine.kod)
            .order_by(UretimVerisi.makine_id)
        )
    ).all()

    # Geri izleme: lotu üreten iş emirlerinin BOM tüketim hareketleri.
    tuketimler: list[IzlenebilirlikTuketimDTO] = []
    if is_emirleri:
        kaynaklar = {f"bom:{ie.id}": ie.kod for ie in is_emirleri}
        hareketler = (
            (
                await db.execute(
                    select(StokHareketi, Malzeme)
                    .join(Malzeme, Malzeme.id == StokHareketi.malzeme_id)
                    .where(StokHareketi.kaynak.in_(list(kaynaklar)))
                    .order_by(StokHareketi.id)
                )
            )
            .tuples()
            .all()
        )
        tuketimler = [
            IzlenebilirlikTuketimDTO(
                malzeme_id=m.id,
                malzeme_kod=m.kod,
                malzeme_ad=m.ad,
                miktar=float(h.miktar),
                is_emri_kod=kaynaklar.get(h.kaynak or "", "?"),
            )
            for h, m in hareketler
        ]

    cevap = IzlenebilirlikCevapDTO(
        lot_no=lot,
        is_emirleri=[
            IzlenebilirlikIsEmriDTO(
                id=ie.id,
                kod=ie.kod,
                durum=ie.durum,
                urun_id=ie.urun_id,
                miktar=float(ie.miktar) if ie.miktar is not None else None,
                kapanis_tarihi=ie.kapanis_tarihi,
            )
            for ie in is_emirleri
        ],
        uretim=[
            IzlenebilirlikUretimDTO(
                makine_id=int(mid),
                makine_kod=str(kod),
                kayit_sayisi=int(sayi),
                toplam_adet=int(toplam),
                saglam_adet=int(saglam),
                ilk_zaman=ilk,
                son_zaman=son,
            )
            for mid, kod, sayi, toplam, saglam, ilk, son in uretim_satirlari
        ],
        tuketilen_malzemeler=tuketimler,
    )
    return basari(cevap.model_dump(), mesaj="İzlenebilirlik zinciri")
