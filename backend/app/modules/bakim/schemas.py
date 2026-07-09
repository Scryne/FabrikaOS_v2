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


class BakimPlaniGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=200)
    tip: str | None = Field(default=None, max_length=20)
    periyot_gun: int | None = Field(default=None, ge=1)
    son_bakim_tarihi: datetime | None = None
    sonraki_bakim_tarihi: datetime | None = None
    aktif: bool | None = None
    aciklama: str | None = Field(default=None, max_length=1000)


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
