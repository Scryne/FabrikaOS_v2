"""Üretim modülü Pydantic DTO'ları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MakineOlusturDTO(BaseModel):
    kod: str = Field(min_length=1, max_length=50)
    ad: str = Field(min_length=1, max_length=200)
    oee_hedefi: float | None = Field(default=None, ge=0, le=1)


class MakineDurumDTO(BaseModel):
    durum: str = Field(min_length=1, max_length=20)


class MakineCevapDTO(BaseModel):
    id: int
    kod: str
    ad: str
    durum: str
    oee_hedefi: float | None = None


class UretimGirisDTO(BaseModel):
    makine_id: int
    zaman: datetime | None = None
    vardiya: str | None = Field(default=None, max_length=20)
    planlanan_sure_dk: float = Field(ge=0)
    durus_sure_dk: float = Field(ge=0)
    toplam_adet: int = Field(ge=0)
    saglam_adet: int = Field(ge=0)
    ideal_cevrim_sn: float = Field(ge=0)


class UretimVerisiCevapDTO(BaseModel):
    id: int
    makine_id: int
    zaman: datetime
    vardiya: str | None = None
    planlanan_sure_dk: float
    durus_sure_dk: float
    toplam_adet: int
    saglam_adet: int
    ideal_cevrim_sn: float


class OeeCevapDTO(BaseModel):
    makine_id: int
    kullanilabilirlik: float
    performans: float
    kalite: float
    oee: float
    kayit_sayisi: int


class OeeOzetSatirDTO(BaseModel):
    makine_id: int
    makine_kod: str
    kullanilabilirlik: float
    performans: float
    kalite: float
    oee: float
    kayit_sayisi: int
