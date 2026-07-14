"""CRM modülü Pydantic DTO'ları (firma + ortak)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# --- Firma ---
class FirmaOlusturDTO(BaseModel):
    ad: str = Field(min_length=1, max_length=200)
    tip: str = Field(default="musteri", max_length=20)
    vergi_no: str = Field(default="", max_length=20)
    vergi_dairesi: str = Field(default="", max_length=100)
    telefon: str = Field(default="", max_length=30)
    eposta: str = Field(default="", max_length=255)
    adres: str = Field(default="", max_length=500)
    il: str = Field(default="", max_length=100)
    sektor: str = Field(default="", max_length=100)
    web_sitesi: str = Field(default="", max_length=255)
    sorumlu_kullanici_id: int | None = None
    aktif: bool = True
    aciklama: str = Field(default="", max_length=2000)


class FirmaGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, max_length=200)
    tip: str | None = Field(default=None, max_length=20)
    vergi_no: str | None = Field(default=None, max_length=20)
    vergi_dairesi: str | None = Field(default=None, max_length=100)
    telefon: str | None = Field(default=None, max_length=30)
    eposta: str | None = Field(default=None, max_length=255)
    adres: str | None = Field(default=None, max_length=500)
    il: str | None = Field(default=None, max_length=100)
    sektor: str | None = Field(default=None, max_length=100)
    web_sitesi: str | None = Field(default=None, max_length=255)
    sorumlu_kullanici_id: int | None = None
    aktif: bool | None = None
    aciklama: str | None = Field(default=None, max_length=2000)


class FirmaCevapDTO(BaseModel):
    id: int
    ad: str
    tip: str
    vergi_no: str
    vergi_dairesi: str
    telefon: str
    eposta: str
    adres: str
    il: str
    sektor: str
    web_sitesi: str
    sorumlu_kullanici_id: int | None = None
    aktif: bool
    aciklama: str
    olusturma_tarihi: datetime


# --- Ortak (firma ilgili kişisi) ---
class OrtakOlusturDTO(BaseModel):
    firma_id: int
    ad_soyad: str = Field(min_length=1, max_length=200)
    unvan: str = Field(default="", max_length=100)
    telefon: str = Field(default="", max_length=30)
    eposta: str = Field(default="", max_length=255)
    birincil: bool = False
    aktif: bool = True
    aciklama: str = Field(default="", max_length=1000)


class OrtakGuncelleDTO(BaseModel):
    ad_soyad: str | None = Field(default=None, max_length=200)
    unvan: str | None = Field(default=None, max_length=100)
    telefon: str | None = Field(default=None, max_length=30)
    eposta: str | None = Field(default=None, max_length=255)
    birincil: bool | None = None
    aktif: bool | None = None
    aciklama: str | None = Field(default=None, max_length=1000)


class OrtakCevapDTO(BaseModel):
    id: int
    firma_id: int
    ad_soyad: str
    unvan: str
    telefon: str
    eposta: str
    birincil: bool
    aktif: bool
    aciklama: str
    olusturma_tarihi: datetime


class TedarikciSkorDTO(BaseModel):
    """Tedarikçi performans skoru (S-VB): 0-100 + bileşen kırılımı + dürüstlük notları."""

    firma_id: int
    skor: float
    kalite_gecme_orani: float
    sozlesme_uyumu: float
    talep_cozum_orani: float
    zamaninda_teslim: float | None = None  # S25 (PO teslim alma) ile dolar
    yetersiz_veri: list[str]
