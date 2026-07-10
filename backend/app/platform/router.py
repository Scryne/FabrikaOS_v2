"""Platform yönetim uçları: ``/api/v1/platform/*`` (kimlik hariç).

Tüm uçlar ``mevcut_platform_yonetici`` korumalıdır; tenant çözümlemesi YOKTUR
(control-plane istisnası — tenant-rbac-conventions). Yazma işlemleri
``platform_denetim_izi``'ne kaydedilir.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Abonelik, Plan, PlatformYonetici, Tenant
from app.core.db.session import get_session
from app.core.responses import Zarf, basari, sayfali
from app.platform import service
from app.platform.deps import mevcut_platform_yonetici
from app.platform.schemas import (
    AbonelikSatirDTO,
    PlanSatirDTO,
    PlatformSaglikDTO,
    TenantDetayDTO,
    TenantOzetDTO,
)

router = APIRouter(prefix="/platform", tags=["Platform"])


@router.get("/tenantlar", response_model=Zarf[list[TenantOzetDTO]], summary="Tenant'ları listele")
async def tenantlari_listele(
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
    arama: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await service.tenant_listele(db, sayfa=sayfa, adet=adet, arama=arama)
    return sayfali([k.model_dump() for k in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/tenantlar/{tenant_id}", response_model=Zarf[TenantDetayDTO], summary="Tenant detayı")
async def tenant_detay(
    tenant_id: int,
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    tenant = await service.tenant_getir(db, tenant_id)
    detay = await service.tenant_detayi(db, tenant)
    return basari(detay.model_dump(), mesaj="Tenant detayı")


@router.get(
    "/abonelikler", response_model=Zarf[list[AbonelikSatirDTO]], summary="Abonelikleri listele"
)
async def abonelikleri_listele(
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    toplam = await db.scalar(select(func.count()).select_from(Abonelik)) or 0
    sonuc = await db.execute(
        select(Abonelik, Tenant)
        .join(Tenant, Abonelik.tenant_id == Tenant.id)
        .order_by(Abonelik.id.desc())
        .offset((sayfa - 1) * adet)
        .limit(adet)
    )
    kayitlar = [
        AbonelikSatirDTO(
            id=ab.id,
            tenant_id=t.id,
            tenant_slug=t.slug,
            tenant_ad=t.ad,
            plan_kodu=ab.plan_kodu,
            durum=ab.durum,
            baslangic_tarihi=ab.baslangic_tarihi,
            bitis_tarihi=ab.bitis_tarihi,
        ).model_dump()
        for ab, t in sonuc.all()
    ]
    return sayfali(kayitlar, sayfa=sayfa, adet=adet, toplam=int(toplam))


@router.get("/planlar", response_model=Zarf[list[PlanSatirDTO]], summary="Plan kataloğu")
async def planlari_listele(
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    sonuc = await db.execute(select(Plan).where(Plan.aktif).order_by(Plan.id))
    kayitlar = [
        PlanSatirDTO(
            kod=p.kod,
            ad=p.ad,
            koltuk_limiti=p.koltuk_limiti,
            moduller=list(p.moduller),
            ozellikler=list(p.ozellikler),
        ).model_dump()
        for p in sonuc.scalars()
    ]
    return basari(kayitlar, mesaj="Plan kataloğu")


@router.get("/saglik", response_model=Zarf[PlatformSaglikDTO], summary="Platform sağlığı")
async def platform_sagligi(
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    durum = await service.saglik_durumu(db)
    return basari(durum.model_dump(), mesaj="Platform sağlığı")
