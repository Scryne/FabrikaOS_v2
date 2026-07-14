"""Bildirim DTO'ları (Pydantic)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class BildirimCevapDTO(BaseModel):
    id: int
    olay_turu: str
    baslik: str
    govde: str
    veri: dict[str, Any]
    onem: str
    okundu: bool
    okundu_tarihi: datetime | None
    olusturma_tarihi: datetime


class BildirimOzetDTO(BaseModel):
    okunmamis: int
    toplam: int
    son: list[BildirimCevapDTO]


class BildirimTercihDTO(BaseModel):
    olay_turu: str
    uygulama_ici: bool
    eposta: bool


class BildirimTercihGuncelleDTO(BaseModel):
    tercihler: list[BildirimTercihDTO] = Field(min_length=1)


class OkunduSayisiDTO(BaseModel):
    guncellenen: int
