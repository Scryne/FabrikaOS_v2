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
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.bakim import repository
from app.modules.bakim.models import BAKIM_TIPLERI, BakimPlani
from app.modules.bakim.schemas import (
    BakimOzetDTO,
    BakimPlaniCevapDTO,
    BakimPlaniGuncelleDTO,
    BakimPlaniOlusturDTO,
    BakimSayiDTO,
)
from app.modules.uretim import repository as uretim_repository

router = APIRouter(tags=["Bakım"])


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
