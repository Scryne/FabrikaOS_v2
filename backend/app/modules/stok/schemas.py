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


class SatinalmaKalemDTO(BaseModel):
    malzeme_id: int
    miktar: Decimal = Field(gt=0)
    birim: str = Field(min_length=1, max_length=20)
    tahmini_birim_fiyat: Decimal | None = Field(default=None, ge=0)
    aciklama: str = Field(default="", max_length=500)


class SatinalmaTalebiOlusturDTO(BaseModel):
    baslik: str = Field(min_length=1, max_length=200)
    aciklama: str = Field(default="", max_length=1000)
    para_birimi: str = Field(default="TRY", min_length=3, max_length=3)
    kalemler: list[SatinalmaKalemDTO] = Field(min_length=1)


class SatinalmaTalebiGuncelleDTO(BaseModel):
    baslik: str | None = Field(default=None, min_length=1, max_length=200)
    aciklama: str | None = Field(default=None, max_length=1000)
    para_birimi: str | None = Field(default=None, min_length=3, max_length=3)
    kalemler: list[SatinalmaKalemDTO] | None = Field(default=None, min_length=1)


class RedDTO(BaseModel):
    red_nedeni: str = Field(default="", max_length=500)


class SatinalmaKalemCevapDTO(BaseModel):
    id: int
    malzeme_id: int
    miktar: float
    birim: str
    tahmini_birim_fiyat: float | None = None
    aciklama: str


class SatinalmaTalebiCevapDTO(BaseModel):
    id: int
    kod: str
    baslik: str
    aciklama: str
    durum: str
    para_birimi: str
    talep_eden_kullanici_id: int | None = None
    onaylayan_kullanici_id: int | None = None
    onay_tarihi: datetime | None = None
    red_nedeni: str | None = None
    tahmini_toplam: float | None = None
    olusturma_tarihi: datetime


class SatinalmaTalebiDetayDTO(SatinalmaTalebiCevapDTO):
    kalemler: list[SatinalmaKalemCevapDTO] = Field(default_factory=list)


class StokOzetDTO(BaseModel):
    """Malzeme/stok KPI özeti (OzetSerit + analiz donut) — salt-okunur."""

    toplam_malzeme: int
    aktif_malzeme: int
    kritik_alti: int
    min_alti: int
    bugun_hareket: int
    kategori_sayisi: int


class SatinalmaSayiDTO(BaseModel):
    durum: str
    adet: int


class SatinalmaOzetDTO(BaseModel):
    """Satınalma talebi KPI özeti (OzetSerit + board sayaçları) — salt-okunur."""

    onay_bekleyen: int
    taslak: int
    onaylandi: int
    reddedildi: int
    toplam: int
    durum_dagilimi: list[SatinalmaSayiDTO]
