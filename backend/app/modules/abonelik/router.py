"""Abonelik & entitlement uçları: ``GET /moduller`` + ``GET /abonelik`` (S16 / ADR-0018).

``/moduller`` yalnız oturum ister (izin yok): frontend menü süzgeci her kullanıcıya
lazımdır ve yalnız modül adı/açıklık bilgisi sızar — menünün zaten gösterdiği bilgi.
``/abonelik`` plan/koltuk ayrıntısı içerir → ``abonelik:oku`` korumalı.

Bu uçlar ÇEKİRDEKTİR (entitlement dependency'si bağlanmaz): kapalı modülleri
listeleyebilmek için her planda erişilebilir kalmalıdır.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane import entitlement_service
from app.control_plane.models import Tenant
from app.control_plane.moduller import MODUL_KATALOGU, OZELLIK_KATALOGU
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, mevcut_kullanici, tenant_cozumle
from app.core.exceptions import KaynakBulunamadi
from app.core.responses import Zarf, basari
from app.kimlik.models import Kullanici
from app.modules.abonelik.schemas import (
    AbonelikCevapDTO,
    KoltukDTO,
    ModulDurumDTO,
    ModullerCevapDTO,
    OzellikDurumDTO,
    PlanDTO,
)

router = APIRouter(tags=["Abonelik"])


async def _modul_durumlari(db: AsyncSession, tenant: Tenant) -> list[ModulDurumDTO]:
    etkin = await entitlement_service.tenant_etkin_moduller(db, tenant)
    haklar = await entitlement_service.hak_haritasi_getir(db, tenant.id)
    return [
        ModulDurumDTO(
            kod=kod,
            ad=MODUL_KATALOGU[kod],
            acik=acik,
            kaynak="hak" if kod in haklar else "plan",
        )
        for kod, acik in etkin.items()
    ]


async def _ozellik_durumlari(db: AsyncSession, tenant: Tenant) -> list[OzellikDurumDTO]:
    etkin = await entitlement_service.tenant_etkin_ozellikler(db, tenant)
    return [
        OzellikDurumDTO(
            kod=kod,
            ad=OZELLIK_KATALOGU[kod].ad,
            acik=acik,
            deneysel=OZELLIK_KATALOGU[kod].deneysel,
        )
        for kod, acik in etkin.items()
    ]


@router.get("/moduller", response_model=Zarf[ModullerCevapDTO], summary="Etkin modüller (menü)")
async def moduller(
    _kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    cevap = ModullerCevapDTO(
        moduller=await _modul_durumlari(db, tenant),
        ozellikler=await _ozellik_durumlari(db, tenant),
    )
    return basari(cevap.model_dump(), mesaj="Etkin modüller")


@router.get("/abonelik", response_model=Zarf[AbonelikCevapDTO], summary="Abonelik özeti")
async def abonelik_ozeti(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("abonelik:oku"))],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    ab = tenant.gecerli_abonelik
    plan = await entitlement_service.plan_getir(db, tenant)
    if ab is None or plan is None:
        # tenant_cozumle geçerli abonelik ister; buraya düşmek plan kaydının
        # silinmesi gibi bir operasyon hatasıdır — görünmez kalsın.
        raise KaynakBulunamadi("Abonelik veya plan kaydı bulunamadı")

    kullanilan = (
        await db.scalar(
            select(func.count()).select_from(Kullanici).where(Kullanici.aktif.is_(True))
        )
        or 0
    )
    cevap = AbonelikCevapDTO(
        plan=PlanDTO(kod=plan.kod, ad=plan.ad, koltuk_limiti=plan.koltuk_limiti),
        durum=ab.durum,
        baslangic_tarihi=ab.baslangic_tarihi,
        bitis_tarihi=ab.bitis_tarihi,
        koltuk=KoltukDTO(limit=plan.koltuk_limiti, kullanilan=int(kullanilan)),
        moduller=await _modul_durumlari(db, tenant),
        ozellikler=await _ozellik_durumlari(db, tenant),
    )
    return basari(cevap.model_dump(), mesaj="Abonelik özeti")
