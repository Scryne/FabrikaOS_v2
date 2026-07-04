"""Talep modülü Pydantic DTO'ları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TalepOlusturDTO(BaseModel):
    firma_id: int | None = None
    baslik: str = Field(min_length=1, max_length=200)
    aciklama: str = Field(default="", max_length=2000)
    tur: str = Field(default="destek", max_length=20)
    oncelik: str = Field(default="orta", max_length=10)
    atanan_kullanici_id: int | None = None
    talep_eden_ad: str = Field(default="", max_length=200)


class TalepGuncelleDTO(BaseModel):
    firma_id: int | None = None
    baslik: str | None = Field(default=None, max_length=200)
    aciklama: str | None = Field(default=None, max_length=2000)
    tur: str | None = Field(default=None, max_length=20)
    oncelik: str | None = Field(default=None, max_length=10)
    atanan_kullanici_id: int | None = None
    talep_eden_ad: str | None = Field(default=None, max_length=200)


class TalepDurumDTO(BaseModel):
    durum: str = Field(min_length=1, max_length=20)


class TalepCevapDTO(BaseModel):
    id: int
    kod: str
    firma_id: int | None = None
    baslik: str
    aciklama: str
    tur: str
    oncelik: str
    durum: str
    atanan_kullanici_id: int | None = None
    talep_eden_kullanici_id: int | None = None
    talep_eden_ad: str
    olusturma_tarihi: datetime
