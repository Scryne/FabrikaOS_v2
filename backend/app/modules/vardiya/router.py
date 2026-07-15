"""Vardiya uçları (``/api/v1/vardiyalar``) — tanım CRUD'u.

Üretim ana-verisi: okuma ``uretim:oku``, yazma ``uretim:yaz``; modül kapısı ``uretim``.
"""

from __future__ import annotations

from datetime import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari
from app.kimlik.models import Kullanici
from app.modules.vardiya.models import Vardiya

router = APIRouter(tags=["Vardiya"], dependencies=[Depends(modul_gerekli("uretim"))])


class VardiyaOlusturDTO(BaseModel):
    ad: str = Field(min_length=1, max_length=50)
    baslangic_saat: time
    bitis_saat: time


class VardiyaGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=50)
    baslangic_saat: time | None = None
    bitis_saat: time | None = None
    aktif: bool | None = None


class VardiyaCevapDTO(BaseModel):
    id: int
    ad: str
    baslangic_saat: time
    bitis_saat: time
    aktif: bool


def _cevap(v: Vardiya) -> dict[str, Any]:
    return VardiyaCevapDTO(
        id=v.id,
        ad=v.ad,
        baslangic_saat=v.baslangic_saat,
        bitis_saat=v.bitis_saat,
        aktif=v.aktif,
    ).model_dump()


@router.get("/vardiyalar", response_model=Zarf[list[VardiyaCevapDTO]], summary="Vardiya tanımları")
async def vardiya_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kayitlar = (await db.execute(select(Vardiya).order_by(Vardiya.baslangic_saat))).scalars().all()
    return basari([_cevap(v) for v in kayitlar], mesaj="Vardiyalar")


@router.post(
    "/vardiyalar",
    response_model=Zarf[VardiyaCevapDTO],
    status_code=201,
    summary="Vardiya tanımı oluştur",
)
async def vardiya_olustur(
    govde: VardiyaOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    mevcut = (
        await db.execute(select(Vardiya.id).where(Vardiya.ad == govde.ad))
    ).scalar_one_or_none()
    if mevcut is not None:
        raise CakismaHatasi("Bu ad ile vardiya zaten var")
    vardiya = Vardiya(ad=govde.ad, baslangic_saat=govde.baslangic_saat, bitis_saat=govde.bitis_saat)
    db.add(vardiya)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="vardiya", kaynak_id=str(vardiya.id), kullanici=kullanici
    )
    return basari(_cevap(vardiya), mesaj="Vardiya oluşturuldu")


@router.patch(
    "/vardiyalar/{vardiya_id}", response_model=Zarf[VardiyaCevapDTO], summary="Vardiya düzenle"
)
async def vardiya_guncelle(
    vardiya_id: int,
    govde: VardiyaGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    vardiya = await db.get(Vardiya, vardiya_id)
    if vardiya is None:
        raise KaynakBulunamadi("Vardiya bulunamadı")
    degisen = govde.model_dump(exclude_unset=True)
    for alan, deger in degisen.items():
        if deger is not None:
            setattr(vardiya, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="vardiya", kaynak_id=str(vardiya.id), kullanici=kullanici
    )
    return basari(_cevap(vardiya), mesaj="Vardiya güncellendi")
