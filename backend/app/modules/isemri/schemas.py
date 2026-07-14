"""İş emri modülü Pydantic DTO'ları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class IsEmriOlusturDTO(BaseModel):
    baslik: str = Field(min_length=1, max_length=200)
    makine_id: int
    aciklama: str = Field(default="", max_length=1000)
    oncelik: str = Field(default="orta", max_length=10)
    kod: str | None = Field(default=None, max_length=50)
    atanan_kullanici_id: int | None = None
    # SLA hedefi (S-VB): boş = SLA takibi yok.
    hedef_tarih: datetime | None = None


class DurumGuncelleDTO(BaseModel):
    durum: str = Field(min_length=1, max_length=20)
    # 'atandi'ya geçişte zorunlu (yoksa ve kayıtta da yoksa 422).
    atanan_kullanici_id: int | None = None


class YorumOlusturDTO(BaseModel):
    metin: str = Field(min_length=1, max_length=2000)


class IsEmriCevapDTO(BaseModel):
    id: int
    kod: str
    baslik: str
    aciklama: str
    makine_id: int
    atanan_kullanici_id: int | None = None
    durum: str
    oncelik: str
    kapanis_tarihi: datetime | None = None
    hedef_tarih: datetime | None = None
    olusturma_tarihi: datetime


class IsEmriYorumCevapDTO(BaseModel):
    id: int
    metin: str
    yazan_kullanici_id: int | None = None
    yazan_eposta: str | None = None
    olusturma_tarihi: datetime


class IsEmriDetayDTO(IsEmriCevapDTO):
    yorumlar: list[IsEmriYorumCevapDTO] = Field(default_factory=list)
