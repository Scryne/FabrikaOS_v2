"""Sözleşme modülü Pydantic DTO'ları."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class SozlesmeOlusturDTO(BaseModel):
    firma_id: int
    baslik: str = Field(min_length=1, max_length=200)
    tur: str = Field(default="hizmet", max_length=20)
    baslangic_tarihi: date
    bitis_tarihi: date
    tutar: Decimal = Field(default=Decimal("0"), ge=0)
    para_birimi: str = Field(default="TRY", max_length=3)
    sorumlu_kullanici_id: int | None = None
    aciklama: str = Field(default="", max_length=2000)


class SozlesmeGuncelleDTO(BaseModel):
    baslik: str | None = Field(default=None, max_length=200)
    tur: str | None = Field(default=None, max_length=20)
    baslangic_tarihi: date | None = None
    bitis_tarihi: date | None = None
    tutar: Decimal | None = Field(default=None, ge=0)
    para_birimi: str | None = Field(default=None, max_length=3)
    sorumlu_kullanici_id: int | None = None
    aciklama: str | None = Field(default=None, max_length=2000)


class SozlesmeDurumDTO(BaseModel):
    durum: str = Field(min_length=1, max_length=20)


class YaklasanTaraDTO(BaseModel):
    esik_gun: int = Field(default=30, ge=1, le=365)


class SozlesmeCevapDTO(BaseModel):
    id: int
    kod: str
    firma_id: int
    baslik: str
    tur: str
    baslangic_tarihi: date
    bitis_tarihi: date
    tutar: float
    para_birimi: str
    durum: str
    sorumlu_kullanici_id: int | None = None
    yaklasim_bildirildi: bool
    aciklama: str
    olusturma_tarihi: datetime


class SozlesmeSayiDTO(BaseModel):
    durum: str
    adet: int


class SozlesmeOzetDTO(BaseModel):
    """Sözleşme KPI özeti (OzetSerit + board sayaçları) — salt-okunur."""

    aktif: int
    yaklasan: int  # aktif + bitiş 30 gün içinde
    taslak: int
    toplam: int
    durum_dagilimi: list[SozlesmeSayiDTO]
