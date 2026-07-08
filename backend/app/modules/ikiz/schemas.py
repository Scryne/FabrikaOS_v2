"""Dijital ikiz DTO'ları (istek/yanıt gövdeleri)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.ikiz.models import KOORDINAT_MAX, KOORDINAT_MIN


class IkizDugumGirisDTO(BaseModel):
    """Yerleşimde bir makine düğümü (yüzde koordinat)."""

    makine_id: int
    x: float = Field(ge=KOORDINAT_MIN, le=KOORDINAT_MAX)
    y: float = Field(ge=KOORDINAT_MIN, le=KOORDINAT_MAX)
    bolge: str = Field(default="", max_length=100)


class YerlesimKaydetDTO(BaseModel):
    """``PUT /ikiz/yerlesim`` gövdesi — şemanın tamamı (replace-all)."""

    dugumler: list[IkizDugumGirisDTO]


class IkizDugumCevapDTO(BaseModel):
    id: int
    makine_id: int
    x: float
    y: float
    bolge: str


class IkizOzetDTO(BaseModel):
    """Tesis geneli pencere özeti (kiosk KPI'ları)."""

    toplam_makine: int
    durumlar: dict[str, int]
    kayit_sayisi: int
    toplam_adet: int
    saglam_adet: int
    fire_orani: float
    oee: float
    acik_ariza: int


class IkizDugumDurumDTO(BaseModel):
    """Yerleşim ⋈ makine — canlı durum + pencere üretim özeti."""

    makine_id: int
    makine_kod: str
    makine_ad: str
    durum: str
    x: float
    y: float
    bolge: str
    oee: float | None
    toplam_adet: int
    son_veri_zamani: datetime | None


class YerlesmemisMakineDTO(BaseModel):
    """Şemaya henüz yerleştirilmemiş makine (düzenleme paleti)."""

    makine_id: int
    makine_kod: str
    makine_ad: str
    durum: str


class IkizDurumCevapDTO(BaseModel):
    """``GET /ikiz/durum`` yanıtı — ikiz görünümü + kiosk tek veri kaynağı."""

    saat: int
    baslangic: datetime
    bitis: datetime
    ozet: IkizOzetDTO
    dugumler: list[IkizDugumDurumDTO]
    yerlesmemis: list[YerlesmemisMakineDTO]
