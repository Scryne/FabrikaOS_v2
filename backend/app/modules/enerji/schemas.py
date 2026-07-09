"""Enerji modülü Pydantic DTO'ları.

İstek tüketimi ``Decimal`` (`gt=0`); cevap tüketimi ``float``. Trend noktası CAGG toplamı.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class EnerjiOlcumOlusturDTO(BaseModel):
    makine_id: int | None = None
    enerji_turu: str = Field(min_length=1, max_length=20)
    tuketim: Decimal = Field(gt=0)
    birim: str = Field(min_length=1, max_length=20)
    zaman: datetime | None = None


class EnerjiOlcumCevapDTO(BaseModel):
    id: int
    makine_id: int | None = None
    enerji_turu: str
    tuketim: float
    birim: str
    zaman: datetime


class EnerjiTrendNoktaDTO(BaseModel):
    zaman: datetime
    toplam: float
    adet: int


class EnerjiOzetDTO(BaseModel):
    """Enerji KPI özeti (OzetSerit) — salt-okunur toplulaştırma."""

    toplam_kayit: int
    bugun_kayit: int
    tur_sayisi: int
    izlenen_makine: int
