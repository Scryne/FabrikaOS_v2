"""Kalite modülü Pydantic DTO'ları.

İstek ölçümleri ``Decimal``; cevap ölçümleri ``float`` (sınırda ``float(...)``). Uygunsuzluk
ve CAPA aksiyon DTO'ları sonraki task'ta eklenir.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class KaliteKontrolOlusturDTO(BaseModel):
    makine_id: int | None = None
    is_emri_id: int | None = None
    kontrol_turu: str = Field(default="uretim", max_length=20)
    sonuc: str = Field(min_length=1, max_length=20)
    olculen_deger: Decimal | None = None
    alt_limit: Decimal | None = None
    ust_limit: Decimal | None = None
    numune_adedi: int = Field(default=0, ge=0)
    uygunsuz_adet: int = Field(default=0, ge=0)
    aciklama: str = Field(default="", max_length=1000)
    zaman: datetime | None = None


class KaliteKontrolCevapDTO(BaseModel):
    id: int
    kod: str
    makine_id: int | None = None
    is_emri_id: int | None = None
    kontrol_turu: str
    sonuc: str
    olculen_deger: float | None = None
    alt_limit: float | None = None
    ust_limit: float | None = None
    numune_adedi: int
    uygunsuz_adet: int
    aciklama: str
    kontrol_eden_kullanici_id: int | None = None
    zaman: datetime
