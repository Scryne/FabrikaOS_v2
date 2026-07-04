"""Duyuru modülü Pydantic DTO'ları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DuyuruOlusturDTO(BaseModel):
    baslik: str = Field(min_length=1, max_length=200)
    icerik: str = Field(default="", max_length=5000)
    onem: str = Field(default="bilgi", max_length=20)
    hedef_departman: str = Field(default="", max_length=100)
    bitis_tarihi: datetime | None = None


class DuyuruGuncelleDTO(BaseModel):
    baslik: str | None = Field(default=None, max_length=200)
    icerik: str | None = Field(default=None, max_length=5000)
    onem: str | None = Field(default=None, max_length=20)
    hedef_departman: str | None = Field(default=None, max_length=100)
    bitis_tarihi: datetime | None = None


class DuyuruCevapDTO(BaseModel):
    id: int
    kod: str
    baslik: str
    icerik: str
    onem: str
    yayinda: bool
    yayin_tarihi: datetime
    bitis_tarihi: datetime | None = None
    hedef_departman: str
    olusturan_kullanici_id: int | None = None
    olusturma_tarihi: datetime
