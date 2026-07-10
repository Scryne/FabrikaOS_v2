"""Dış portal DTO'ları — iç talep DTO'sunun müşteriye açık alt kümesi.

İç alanlar (``atanan_kullanici_id``, ``firma_id`` vb.) bilinçli olarak DIŞARIDA:
dış kullanıcı kendi firmasının bağlamındadır, iç atama/ilişki bilgisi sızmaz.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DisTalepOlusturDTO(BaseModel):
    baslik: str = Field(min_length=1, max_length=200)
    aciklama: str = Field(default="", max_length=2000)
    tur: str = Field(default="destek", max_length=20)
    oncelik: str = Field(default="orta", max_length=10)


class DisTalepCevapDTO(BaseModel):
    id: int
    kod: str
    baslik: str
    aciklama: str
    tur: str
    oncelik: str
    durum: str
    olusturma_tarihi: datetime
    guncelleme_tarihi: datetime


class DisDurumSayiDTO(BaseModel):
    durum: str
    adet: int


class DisDurumDTO(BaseModel):
    """Portal özet ekranı: firma bağlamı + talep durum kırılımı + son talepler."""

    firma_ad: str
    toplam: int
    acik: int
    durum_dagilimi: list[DisDurumSayiDTO]
    son_talepler: list[DisTalepCevapDTO]
