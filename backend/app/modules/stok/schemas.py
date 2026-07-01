"""Stok & Satınalma Pydantic DTO'ları.

İstek miktarları ``Decimal`` (kesinlik); cevap miktarları ``float`` (JSON sayı, sınırda
``float(...)`` dönüşümü). Hareket ve satınalma DTO'ları sonraki task'larda eklenir.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class MalzemeOlusturDTO(BaseModel):
    kod: str = Field(min_length=1, max_length=50)
    ad: str = Field(min_length=1, max_length=200)
    birim: str = Field(min_length=1, max_length=20)
    kategori: str = Field(default="", max_length=100)
    min_stok: Decimal = Field(default=Decimal(0), ge=0)
    max_stok: Decimal | None = Field(default=None, ge=0)
    kritik_stok: Decimal = Field(default=Decimal(0), ge=0)


class MalzemeGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=200)
    birim: str | None = Field(default=None, min_length=1, max_length=20)
    kategori: str | None = Field(default=None, max_length=100)
    min_stok: Decimal | None = Field(default=None, ge=0)
    max_stok: Decimal | None = Field(default=None, ge=0)
    kritik_stok: Decimal | None = Field(default=None, ge=0)
    aktif: bool | None = None


class MalzemeCevapDTO(BaseModel):
    id: int
    kod: str
    ad: str
    birim: str
    kategori: str
    mevcut_miktar: float
    min_stok: float
    max_stok: float | None = None
    kritik_stok: float
    aktif: bool
    kritik: bool
    olusturma_tarihi: datetime


class StokHareketiOlusturDTO(BaseModel):
    malzeme_id: int
    tur: str = Field(min_length=1, max_length=10)
    miktar: Decimal = Field(gt=0)
    aciklama: str = Field(default="", max_length=500)
    kaynak: str | None = Field(default=None, max_length=50)


class StokHareketiCevapDTO(BaseModel):
    id: int
    malzeme_id: int
    tur: str
    miktar: float
    bakiye_sonrasi: float
    aciklama: str
    kaynak: str | None = None
    olusturan_kullanici_id: int | None = None
    olusturma_tarihi: datetime
