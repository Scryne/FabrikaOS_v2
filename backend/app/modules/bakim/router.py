"""Bakım modülü uçları (``/api/v1``).

Tenant-kapsamlı ve RBAC korumalı (``bakim:oku`` / ``bakim:yaz``). Yazma işlemleri
denetim izine kaydedilir. Bu sprintte bakım planları yalnızca CRUD'dur.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.bakim import repository, service
from app.modules.bakim.metrik import mtbf_mttr_hesapla
from app.modules.bakim.models import BAKIM_TIPLERI, BakimPlani
from app.modules.bakim.schemas import (
    BakimOzetDTO,
    BakimPlaniCevapDTO,
    BakimPlaniGuncelleDTO,
    BakimPlaniOlusturDTO,
    BakimSayiDTO,
    MtbfMttrCevapDTO,
    VadeTaramaCevapDTO,
)
from app.modules.uretim import repository as uretim_repository
from app.modules.uretim.models import ArizaKaydi

router = APIRouter(tags=["Bakım"], dependencies=[Depends(modul_gerekli("bakim"))])


def _cevap(p: BakimPlani) -> dict[str, Any]:
    return BakimPlaniCevapDTO(
        id=p.id,
        makine_id=p.makine_id,
        ad=p.ad,
        tip=p.tip,
        periyot_gun=p.periyot_gun,
        son_bakim_tarihi=p.son_bakim_tarihi,
        sonraki_bakim_tarihi=p.sonraki_bakim_tarihi,
        aktif=p.aktif,
        aciklama=p.aciklama,
        yedek_parca_malzeme_id=p.yedek_parca_malzeme_id,
    ).model_dump()


def _tip_dogrula(tip: str) -> None:
    if tip not in BAKIM_TIPLERI:
        raise DogrulamaHatasi(
            "Geçersiz bakım tipi",
            detaylar=[{"alan": "tip", "mesaj": f"Geçerli: {', '.join(sorted(BAKIM_TIPLERI))}"}],
        )


@router.post(
    "/bakim-planlari",
    response_model=Zarf[BakimPlaniCevapDTO],
    status_code=201,
    summary="Bakım planı oluştur",
)
async def bakim_olustur(
    govde: BakimPlaniOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("bakim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    _tip_dogrula(govde.tip)
    if await uretim_repository.makine_getir(db, govde.makine_id) is None:
        raise KaynakBulunamadi("Makine bulunamadı")
    plan = BakimPlani(
        makine_id=govde.makine_id,
        ad=govde.ad,
        tip=govde.tip,
        periyot_gun=govde.periyot_gun,
        son_bakim_tarihi=govde.son_bakim_tarihi,
        sonraki_bakim_tarihi=govde.sonraki_bakim_tarihi,
        aciklama=govde.aciklama,
        yedek_parca_malzeme_id=govde.yedek_parca_malzeme_id,
    )
    await repository.ekle(db, plan)
    await denetim_yaz(
        db, eylem="olustur", kaynak="bakim_plani", kaynak_id=str(plan.id), kullanici=kullanici
    )
    return basari(_cevap(plan), mesaj="Bakım planı oluşturuldu")


@router.get(
    "/bakim-planlari",
    response_model=Zarf[list[BakimPlaniCevapDTO]],
    summary="Bakım planlarını listele",
)
async def bakim_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("bakim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
    makine_id: int | None = None,
    aktif: bool | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.listele(
        db,
        sayfa=sayfa,
        adet=adet,
        makine_id=makine_id,
        aktif=aktif,
        arama=arama,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_cevap(p) for p in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/bakim-planlari/{plan_id}",
    response_model=Zarf[BakimPlaniCevapDTO],
    summary="Bakım planı detayı",
)
async def bakim_detay(
    plan_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("bakim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    plan = await repository.getir(db, plan_id)
    if plan is None:
        raise KaynakBulunamadi("Bakım planı bulunamadı")
    return basari(_cevap(plan), mesaj="Bakım planı detayı")


@router.patch(
    "/bakim-planlari/{plan_id}",
    response_model=Zarf[BakimPlaniCevapDTO],
    summary="Bakım planını güncelle",
)
async def bakim_guncelle(
    plan_id: int,
    govde: BakimPlaniGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("bakim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    plan = await repository.getir(db, plan_id)
    if plan is None:
        raise KaynakBulunamadi("Bakım planı bulunamadı")
    degisiklikler = govde.model_dump(exclude_unset=True)
    if "tip" in degisiklikler and degisiklikler["tip"] is not None:
        _tip_dogrula(degisiklikler["tip"])
    for alan, deger in degisiklikler.items():
        setattr(plan, alan, deger)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="guncelle",
        kaynak="bakim_plani",
        kaynak_id=str(plan.id),
        kullanici=kullanici,
        # JSONB için güvenli: datetime'lar ISO-8601 string'e dönüşür.
        detay=govde.model_dump(exclude_unset=True, mode="json"),
    )
    return basari(_cevap(plan), mesaj="Bakım planı güncellendi")


@router.get("/bakim/ozet", response_model=Zarf[BakimOzetDTO], summary="Bakım özeti (KPI)")
async def bakim_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("bakim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    simdi = datetime.now(UTC)
    hafta_sonu = simdi + timedelta(days=7)

    toplam = await db.scalar(select(func.count()).select_from(BakimPlani)) or 0
    aktif = (
        await db.scalar(
            select(func.count()).select_from(BakimPlani).where(BakimPlani.aktif.is_(True))
        )
        or 0
    )
    bu_hafta = (
        await db.scalar(
            select(func.count())
            .select_from(BakimPlani)
            .where(
                BakimPlani.aktif.is_(True),
                BakimPlani.sonraki_bakim_tarihi >= simdi,
                BakimPlani.sonraki_bakim_tarihi <= hafta_sonu,
            )
        )
        or 0
    )
    gecikmis = (
        await db.scalar(
            select(func.count())
            .select_from(BakimPlani)
            .where(BakimPlani.aktif.is_(True), BakimPlani.sonraki_bakim_tarihi < simdi)
        )
        or 0
    )
    tip_sonuc = await db.execute(select(BakimPlani.tip, func.count()).group_by(BakimPlani.tip))
    tip_dagilimi = [BakimSayiDTO(ad=tip, adet=int(a)) for tip, a in tip_sonuc.all()]

    ozet = BakimOzetDTO(
        aktif_plan=int(aktif),
        bu_hafta_vadesi=int(bu_hafta),
        gecikmis=int(gecikmis),
        toplam_plan=int(toplam),
        tip_dagilimi=tip_dagilimi,
    )
    return basari(ozet.model_dump(), mesaj="Bakım özeti")


@router.post(
    "/bakim-planlari/vade-tara",
    response_model=Zarf[VadeTaramaCevapDTO],
    summary="Vade taraması — vadesi gelen planlardan otomatik iş emri üret (bir-kez)",
)
async def bakim_vade_tara(
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("bakim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    uretilen = await service.vade_tara(db, kullanici=kullanici)
    await denetim_yaz(
        db,
        eylem="vade_tara",
        kaynak="bakim_plani",
        kaynak_id="-",
        kullanici=kullanici,
        detay={"uretilen_is_emri": uretilen},
    )
    if uretilen:
        await yayinla(tenant.slug, {"tur": "isemri.olusturuldu"})
    return basari(VadeTaramaCevapDTO(uretilen_is_emri=uretilen).model_dump(), mesaj="Vade taraması")


@router.get(
    "/bakim/metrikler",
    response_model=Zarf[MtbfMttrCevapDTO],
    summary="Makine güvenilirlik metrikleri (MTBF/MTTR)",
)
async def bakim_metrikleri(
    makine_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("bakim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    gun: int = 90,
) -> dict[str, Any]:
    gun = min(max(gun, 1), 365)
    if await uretim_repository.makine_getir(db, makine_id) is None:
        raise KaynakBulunamadi("Makine bulunamadı")
    simdi = datetime.now(UTC)
    baslangic = simdi - timedelta(days=gun)
    kayitlar = (
        (
            await db.execute(
                select(ArizaKaydi.baslangic, ArizaKaydi.bitis).where(
                    ArizaKaydi.makine_id == makine_id,
                    ArizaKaydi.baslangic <= simdi,
                    (ArizaKaydi.bitis.is_(None)) | (ArizaKaydi.bitis >= baslangic),
                )
            )
        )
        .tuples()
        .all()
    )
    sonuc = mtbf_mttr_hesapla(
        [(b, e) for b, e in kayitlar], pencere_baslangic=baslangic, pencere_bitis=simdi
    )
    return basari(
        MtbfMttrCevapDTO(
            makine_id=makine_id,
            gun=gun,
            ariza_sayisi=sonuc.ariza_sayisi,
            kapanan_ariza=sonuc.kapanan_ariza,
            toplam_ariza_saat=sonuc.toplam_ariza_saat,
            mtbf_saat=sonuc.mtbf_saat,
            mttr_saat=sonuc.mttr_saat,
        ).model_dump(),
        mesaj="MTBF/MTTR",
    )
