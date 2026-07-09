"""Abonelik/entitlement DTO'ları (S16)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ModulDurumDTO(BaseModel):
    """Bir modülün tenant için etkin durumu; ``kaynak`` kararın nereden geldiğini söyler."""

    kod: str
    ad: str
    acik: bool
    kaynak: Literal["plan", "hak"]


class OzellikDurumDTO(BaseModel):
    """Bir özellik bayrağının tenant için etkin durumu."""

    kod: str
    ad: str
    acik: bool
    deneysel: bool


class ModullerCevapDTO(BaseModel):
    """`GET /moduller` yanıtı — menü süzgeci için hafif görünürlük verisi."""

    moduller: list[ModulDurumDTO]
    ozellikler: list[OzellikDurumDTO]


class PlanDTO(BaseModel):
    kod: str
    ad: str
    koltuk_limiti: int | None


class KoltukDTO(BaseModel):
    """Koltuk kullanımı; ``limit=None`` sınırsız demektir."""

    limit: int | None
    kullanilan: int


class AbonelikCevapDTO(BaseModel):
    """`GET /abonelik` yanıtı — plan künyesi + dönem + koltuk + modül/özellik matrisi."""

    plan: PlanDTO
    durum: str
    baslangic_tarihi: datetime
    bitis_tarihi: datetime | None
    koltuk: KoltukDTO
    moduller: list[ModulDurumDTO]
    ozellikler: list[OzellikDurumDTO]
