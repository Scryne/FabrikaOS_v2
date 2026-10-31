"""İçe aktarma DTO'ları (S21)."""

from __future__ import annotations

from pydantic import BaseModel


class AlanDTO(BaseModel):
    ad: str
    zorunlu: bool
    aciklama: str
    ornek: str


class TurDTO(BaseModel):
    kod: str
    baslik: str
    aciklama: str
    anahtar: list[str]
    yetkili: bool
    alanlar: list[AlanDTO]


class SatirHatasiDTO(BaseModel):
    alan: str
    mesaj: str


class SatirSonucuDTO(BaseModel):
    satir: int
    anahtar: str
    islem: str
    hatalar: list[SatirHatasiDTO]
    degisen: list[str]


class OnizlemeDTO(BaseModel):
    tur: str
    toplam: int
    yeni: int
    guncelle: int
    ayni: int
    hatali: int
    eksik_kolonlar: list[str]
    bilinmeyen_kolonlar: list[str]
    satirlar: list[SatirSonucuDTO]
