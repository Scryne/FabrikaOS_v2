"""Planlama uçları (``/api/v1``, S30 / ADR-0049): okuma ``planlama:oku``, girdi ``planlama:yaz``."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari
from app.core.zaman import is_gunu
from app.kimlik.models import Kullanici
from app.modules.isemri.models import IsEmri
from app.modules.planlama import service
from app.modules.planlama.models import IsEmriPlani

router = APIRouter(tags=["Planlama"], dependencies=[Depends(modul_gerekli("planlama"))])
Oturum = Annotated[AsyncSession, Depends(get_session)]


class ZamanAraligiDTO(BaseModel):
    baslangic: datetime
    bitis: datetime


class CizelgeIsiDTO(BaseModel):
    is_emri_id: int
    kod: str
    baslik: str
    durum: str
    oncelik: str
    hedef_tarih: datetime | None
    sure_dk: float
    sure_kaynagi: str
    elle_sira: int | None
    baslangic: datetime | None
    bitis: datetime | None
    parcalar: list[ZamanAraligiDTO]
    gecikme_dk: float
    sigmadi: bool
    kapasite_asimi: bool
    sira_kaynakli_gecikme: bool


class GunlukYukDTO(BaseModel):
    gun: date
    plan_dk: float
    kapasite_dk: float


class MakineCizelgesiDTO(BaseModel):
    makine_id: int
    kod: str
    ad: str
    isler: list[CizelgeIsiDTO]
    gunluk_yuk: list[GunlukYukDTO]


class CizelgeOzetDTO(BaseModel):
    is_sayisi: int
    geciken: int
    kapasite_asimi: int
    varsayilan_sure: int


class CizelgeDTO(BaseModel):
    baslangic: datetime
    bitis: datetime
    varsayilan_vardiya: bool
    pencereler: list[ZamanAraligiDTO]
    makineler: list[MakineCizelgesiDTO]
    ozet: CizelgeOzetDTO


class PlanGirdisiDTO(BaseModel):
    """İkisi de boşsa plan girdisi silinir (süre tahmine, sıra EDD'ye döner)."""

    sure_dk: float | None = Field(default=None, gt=0, le=60 * 24 * 60)
    elle_sira: int | None = Field(default=None, ge=1, le=10_000)


class PlanCevapDTO(BaseModel):
    is_emri_id: int
    sure_dk: float | None
    elle_sira: int | None


@router.get(
    "/planlama/cizelge", response_model=Zarf[CizelgeDTO], summary="Sonlu kapasite çizelgesi"
)
async def planlama_cizelge(
    _k: Annotated[Kullanici, Depends(izin_gerekli("planlama:oku"))],
    db: Oturum,
    _t: Annotated[object, Depends(tenant_cozumle)],
    baslangic: date | None = None,
    gun: Annotated[int, Query(ge=1, le=31)] = 7,
    makine_id: Annotated[int | None, Query(ge=1, le=2**63 - 1)] = None,
) -> dict[str, Any]:
    veri = await service.cizelge_hesapla(
        db, ilk_gun=baslangic or is_gunu(), gun_sayisi=gun, makine_id=makine_id
    )
    return basari(CizelgeDTO(**veri).model_dump(), mesaj="Çizelge")


@router.put(
    "/is-emirleri/{is_emri_id}/plan",
    response_model=Zarf[PlanCevapDTO],
    summary="İş emri plan girdisi (elle süre / elle sıra)",
)
async def plan_girdisi(
    is_emri_id: int,
    govde: PlanGirdisiDTO,
    k: Annotated[Kullanici, Depends(izin_gerekli("planlama:yaz"))],
    db: Oturum,
    _t: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    ie = await db.get(IsEmri, is_emri_id)
    if ie is None:
        raise KaynakBulunamadi("İş emri bulunamadı")
    if ie.durum not in service.ACIK_DURUMLAR:
        raise CakismaHatasi("Kapanmış ya da iptal edilmiş iş emri planlanmaz")
    plan = await db.scalar(
        select(IsEmriPlani).where(IsEmriPlani.is_emri_id == is_emri_id).with_for_update()
    )
    if govde.sure_dk is None and govde.elle_sira is None:
        if plan is not None:
            await db.delete(plan)
    else:
        if plan is None:
            plan = IsEmriPlani(is_emri_id=is_emri_id)
            db.add(plan)
        plan.sure_dk = govde.sure_dk  # type: ignore[assignment]
        plan.elle_sira = govde.elle_sira
    await db.flush()
    await denetim_yaz(
        db,
        eylem="planla",
        kaynak="is_emri",
        kaynak_id=str(is_emri_id),
        kullanici=k,
        detay=govde.model_dump(),
    )
    return basari(
        PlanCevapDTO(
            is_emri_id=is_emri_id, sure_dk=govde.sure_dk, elle_sira=govde.elle_sira
        ).model_dump(),
        mesaj="Plan girdisi kaydedildi",
    )
