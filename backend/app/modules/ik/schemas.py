"""İK modülü Pydantic DTO'ları (personel + izin/mesai/zimmet/sertifika).

KVKK: ``PersonelCevapDTO.tc_kimlik_no`` maskeli döner (router ``tc_maskele`` uygular).
İstek DTO'larında girilen ham TC saklanır; asla maskesiz yansıtılmaz.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# --- Personel ---
class PersonelOlusturDTO(BaseModel):
    sicil_no: str = Field(min_length=1, max_length=50)
    ad: str = Field(min_length=1, max_length=100)
    soyad: str = Field(min_length=1, max_length=100)
    tc_kimlik_no: str = Field(default="", max_length=11)
    dogum_tarihi: date | None = None
    telefon: str = Field(default="", max_length=30)
    eposta: str = Field(default="", max_length=255)
    departman: str = Field(default="", max_length=100)
    unvan: str = Field(default="", max_length=100)
    ise_giris_tarihi: date | None = None
    yillik_izin_hakki: int = Field(default=14, ge=0)
    kullanici_id: int | None = None
    aktif: bool = True


class PersonelGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, max_length=100)
    soyad: str | None = Field(default=None, max_length=100)
    tc_kimlik_no: str | None = Field(default=None, max_length=11)
    dogum_tarihi: date | None = None
    telefon: str | None = Field(default=None, max_length=30)
    eposta: str | None = Field(default=None, max_length=255)
    departman: str | None = Field(default=None, max_length=100)
    unvan: str | None = Field(default=None, max_length=100)
    ise_giris_tarihi: date | None = None
    yillik_izin_hakki: int | None = Field(default=None, ge=0)
    kullanici_id: int | None = None
    aktif: bool | None = None


class PersonelCevapDTO(BaseModel):
    id: int
    sicil_no: str
    ad: str
    soyad: str
    tc_kimlik_no: str  # KVKK: maskeli (yalnız son 2 hane)
    dogum_tarihi: date | None = None
    telefon: str
    eposta: str
    departman: str
    unvan: str
    ise_giris_tarihi: date | None = None
    yillik_izin_hakki: int
    kullanici_id: int | None = None
    aktif: bool
    olusturma_tarihi: datetime


# --- İzin talebi ---
class IzinTalebiOlusturDTO(BaseModel):
    personel_id: int
    izin_turu: str = Field(default="yillik", max_length=20)
    baslangic_tarihi: date
    bitis_tarihi: date
    aciklama: str = Field(default="", max_length=1000)


class IzinTalebiGuncelleDTO(BaseModel):
    izin_turu: str | None = Field(default=None, max_length=20)
    baslangic_tarihi: date | None = None
    bitis_tarihi: date | None = None
    aciklama: str | None = Field(default=None, max_length=1000)


class IzinTalebiCevapDTO(BaseModel):
    id: int
    kod: str
    personel_id: int
    izin_turu: str
    baslangic_tarihi: date
    bitis_tarihi: date
    gun_sayisi: int
    aciklama: str
    durum: str
    talep_eden_kullanici_id: int | None = None
    onaylayan_kullanici_id: int | None = None
    onay_tarihi: datetime | None = None
    red_nedeni: str
    olusturma_tarihi: datetime


class RedDTO(BaseModel):
    red_nedeni: str = Field(min_length=1, max_length=1000)


# --- Fazla mesai ---
class FazlaMesaiOlusturDTO(BaseModel):
    personel_id: int
    tarih: date
    saat: Decimal = Field(gt=0)
    aciklama: str = Field(default="", max_length=1000)


class FazlaMesaiCevapDTO(BaseModel):
    id: int
    personel_id: int
    tarih: date
    saat: float
    aciklama: str
    onayli: bool
    olusturan_kullanici_id: int | None = None
    olusturma_tarihi: datetime


# --- Zimmet ---
class ZimmetOlusturDTO(BaseModel):
    personel_id: int
    demirbas: str = Field(min_length=1, max_length=200)
    seri_no: str = Field(default="", max_length=100)
    zimmet_tarihi: date
    aciklama: str = Field(default="", max_length=1000)


class ZimmetCevapDTO(BaseModel):
    id: int
    personel_id: int
    demirbas: str
    seri_no: str
    zimmet_tarihi: date
    iade_tarihi: date | None = None
    durum: str
    aciklama: str
    olusturma_tarihi: datetime


# --- Sertifika ---
class SertifikaOlusturDTO(BaseModel):
    personel_id: int
    ad: str = Field(min_length=1, max_length=200)
    kurum: str = Field(default="", max_length=200)
    belge_no: str = Field(default="", max_length=100)
    alinma_tarihi: date
    gecerlilik_tarihi: date | None = None
    aciklama: str = Field(default="", max_length=1000)


class SertifikaCevapDTO(BaseModel):
    id: int
    personel_id: int
    ad: str
    kurum: str
    belge_no: str
    alinma_tarihi: date
    gecerlilik_tarihi: date | None = None
    aciklama: str
    olusturma_tarihi: datetime


class IkOzetDTO(BaseModel):
    """İK KPI özeti (OzetSerit) — salt-okunur toplulaştırma."""

    aktif_personel: int
    toplam_personel: int
    bugun_izinli: int
    yaklasan_sertifika: int  # geçerliliği 30 gün içinde bitecek
    acik_zimmet: int
