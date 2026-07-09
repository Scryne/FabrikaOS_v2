"""Kalite modülü Pydantic DTO'ları.

İstek ölçümleri ``Decimal``; cevap ölçümleri ``float`` (sınırda ``float(...)``). Uygunsuzluk
ve CAPA aksiyon DTO'ları sonraki task'ta eklenir.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class KaliteKontrolOlusturDTO(BaseModel):
    makine_id: int | None = None
    is_emri_id: int | None = None
    kontrol_turu: str = Field(default="uretim", max_length=20)
    sonuc: str = Field(min_length=1, max_length=20)
    olculen_deger: Decimal | None = None
    alt_limit: Decimal | None = None
    ust_limit: Decimal | None = None
    numune_adedi: int = Field(default=0, ge=0)
    uygunsuz_adet: int = Field(default=0, ge=0)
    aciklama: str = Field(default="", max_length=1000)
    zaman: datetime | None = None


class KaliteKontrolCevapDTO(BaseModel):
    id: int
    kod: str
    makine_id: int | None = None
    is_emri_id: int | None = None
    kontrol_turu: str
    sonuc: str
    olculen_deger: float | None = None
    alt_limit: float | None = None
    ust_limit: float | None = None
    numune_adedi: int
    uygunsuz_adet: int
    aciklama: str
    kontrol_eden_kullanici_id: int | None = None
    zaman: datetime


class UygunsuzlukOlusturDTO(BaseModel):
    baslik: str = Field(min_length=1, max_length=200)
    aciklama: str = Field(default="", max_length=2000)
    onem: str = Field(default="orta", max_length=20)
    kaynak_kontrol_id: int | None = None
    makine_id: int | None = None
    sorumlu_kullanici_id: int | None = None


class UygunsuzlukGuncelleDTO(BaseModel):
    baslik: str | None = Field(default=None, min_length=1, max_length=200)
    aciklama: str | None = Field(default=None, max_length=2000)
    onem: str | None = Field(default=None, max_length=20)
    sorumlu_kullanici_id: int | None = None


class DurumGecisDTO(BaseModel):
    hedef: str = Field(min_length=1, max_length=20)
    kok_neden: str | None = Field(default=None, max_length=2000)
    dogrulama_notu: str | None = Field(default=None, max_length=2000)


class AksiyonOlusturDTO(BaseModel):
    tur: str = Field(min_length=1, max_length=20)
    aciklama: str = Field(min_length=1, max_length=1000)
    sorumlu_kullanici_id: int | None = None
    termin_tarihi: datetime | None = None


class AksiyonGuncelleDTO(BaseModel):
    durum: str | None = Field(default=None, max_length=20)
    aciklama: str | None = Field(default=None, min_length=1, max_length=1000)
    sorumlu_kullanici_id: int | None = None
    termin_tarihi: datetime | None = None


class AksiyonCevapDTO(BaseModel):
    id: int
    tur: str
    aciklama: str
    sorumlu_kullanici_id: int | None = None
    termin_tarihi: datetime | None = None
    durum: str
    tamamlanma_tarihi: datetime | None = None


class UygunsuzlukCevapDTO(BaseModel):
    id: int
    kod: str
    baslik: str
    aciklama: str
    kaynak_kontrol_id: int | None = None
    makine_id: int | None = None
    onem: str
    durum: str
    kok_neden: str
    acan_kullanici_id: int | None = None
    sorumlu_kullanici_id: int | None = None
    dogrulama_notu: str
    kapanis_tarihi: datetime | None = None
    olusturma_tarihi: datetime


class UygunsuzlukDetayDTO(UygunsuzlukCevapDTO):
    aksiyonlar: list[AksiyonCevapDTO] = Field(default_factory=list)


class KaliteOzetDTO(BaseModel):
    """Kalite/CAPA KPI özeti (OzetSerit) — salt-okunur toplulaştırma."""

    acik_uygunsuzluk: int
    dogrulamada: int
    kapali_uygunsuzluk: int
    bu_ay_kapanan: int
    toplam_uygunsuzluk: int
    toplam_kontrol: int
    gecti_kontrol: int
    gecti_orani: float  # 0–1 (kalite kontrol geçme oranı)
