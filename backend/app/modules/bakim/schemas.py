"""Bakım modülü Pydantic DTO'ları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BakimPlaniOlusturDTO(BaseModel):
    makine_id: int
    ad: str = Field(min_length=1, max_length=200)
    tip: str = Field(default="onleyici", max_length=20)
    periyot_gun: int | None = Field(default=None, ge=1)
    son_bakim_tarihi: datetime | None = None
    sonraki_bakim_tarihi: datetime | None = None
    aciklama: str = Field(default="", max_length=1000)
    # Yedek parça = malzeme ilişkisi (S24).
    yedek_parca_malzeme_id: int | None = None


class BakimPlaniGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=200)
    tip: str | None = Field(default=None, max_length=20)
    periyot_gun: int | None = Field(default=None, ge=1)
    son_bakim_tarihi: datetime | None = None
    sonraki_bakim_tarihi: datetime | None = None
    aktif: bool | None = None
    aciklama: str | None = Field(default=None, max_length=1000)
    yedek_parca_malzeme_id: int | None = None


class BakimPlaniCevapDTO(BaseModel):
    id: int
    makine_id: int
    ad: str
    tip: str
    periyot_gun: int | None = None
    son_bakim_tarihi: datetime | None = None
    sonraki_bakim_tarihi: datetime | None = None
    aktif: bool
    aciklama: str
    yedek_parca_malzeme_id: int | None = None


class BakimSayiDTO(BaseModel):
    ad: str
    adet: int


class BakimOzetDTO(BaseModel):
    """Bakım planı KPI özeti (OzetSerit) — salt-okunur toplulaştırma."""

    aktif_plan: int
    bu_hafta_vadesi: int
    gecikmis: int
    toplam_plan: int
    tip_dagilimi: list[BakimSayiDTO]


class VadeTaramaCevapDTO(BaseModel):
    """Vade taraması sonucu: üretilen otomatik bakım iş emri sayısı."""

    uretilen_is_emri: int


class MtbfMttrCevapDTO(BaseModel):
    """Makine güvenilirlik metrikleri (S24) — arıza yoksa metrikler null."""

    makine_id: int
    gun: int
    ariza_sayisi: int
    kapanan_ariza: int
    toplam_ariza_saat: float
    mtbf_saat: float | None = None
    mttr_saat: float | None = None
