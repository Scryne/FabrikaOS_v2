"""Ticari özet DTO'ları (pano)."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class TicariSayaclarDTO(BaseModel):
    firma_sayisi: int
    aktif_firma: int
    aktif_sozlesme: int
    yaklasan_sozlesme: int
    acik_talep: int
    yayinli_duyuru: int


class YaklasanSozlesmeDTO(BaseModel):
    id: int
    kod: str
    firma_id: int
    baslik: str
    bitis_tarihi: date
    kalan_gun: int
    tutar: float
    para_birimi: str


class SonDuyuruDTO(BaseModel):
    id: int
    kod: str
    baslik: str
    onem: str
    yayin_tarihi: datetime


class TicariOzetDTO(BaseModel):
    sayaclar: TicariSayaclarDTO
    yaklasan_sozlesmeler: list[YaklasanSozlesmeDTO]
    son_duyurular: list[SonDuyuruDTO]
