"""DYS modülü Pydantic DTO'ları (belge + sürüm).

``BelgeSurumuCevapDTO`` iç ``nesne_anahtari``'nı **açığa çıkarmaz** (depolama detayı gizli).
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BelgeOlusturDTO(BaseModel):
    ad: str = Field(min_length=1, max_length=200)
    kategori: str = Field(default="", max_length=100)
    aciklama: str = Field(default="", max_length=1000)


class BelgeGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, max_length=200)
    kategori: str | None = Field(default=None, max_length=100)
    aciklama: str | None = Field(default=None, max_length=1000)
    aktif: bool | None = None


class BelgeCevapDTO(BaseModel):
    id: int
    kod: str
    ad: str
    kategori: str
    aciklama: str
    guncel_surum: int
    aktif: bool
    olusturan_kullanici_id: int | None = None
    olusturma_tarihi: datetime


class BelgeSurumuCevapDTO(BaseModel):
    id: int
    belge_id: int
    surum_no: int
    dosya_adi: str
    icerik_tipi: str
    boyut: int
    yukleyen_kullanici_id: int | None = None
    aciklama: str
    olusturma_tarihi: datetime
