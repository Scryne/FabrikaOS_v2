"""Entegrasyon DTO'ları (webhook aboneliği + teslimat günlüğü)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WebhookOlusturDTO(BaseModel):
    ad: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=1, max_length=500)
    # Katalogdan alt küme; boş liste = tüm olay türleri.
    olay_turleri: list[str] = Field(default_factory=list)
    aktif: bool = True


class WebhookGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=120)
    url: str | None = Field(default=None, min_length=1, max_length=500)
    olay_turleri: list[str] | None = None
    aktif: bool | None = None


class WebhookCevapDTO(BaseModel):
    """Abonelik yanıtı — ``gizli_anahtar`` listede/detayda MASKELİDİR; yalnız
    oluşturma ve anahtar-yenile yanıtlarında tam değer döner (bir kez)."""

    id: int
    ad: str
    url: str
    gizli_anahtar: str
    olay_turleri: list[str]
    aktif: bool
    olusturma_tarihi: datetime


class TeslimatCevapDTO(BaseModel):
    id: int
    dis_anahtar: uuid.UUID
    abonelik_id: int
    olay_turu: str
    durum: str
    deneme_sayisi: int
    sonraki_deneme_tarihi: datetime
    son_deneme_tarihi: datetime | None
    yanit_kodu: int | None
    yanit_ozeti: str
    govde: dict[str, Any]
    olusturma_tarihi: datetime


class OlayTuruCevapDTO(BaseModel):
    kod: str
    aciklama: str


# --- API anahtarı ---


class ApiAnahtariOlusturDTO(BaseModel):
    ad: str = Field(min_length=1, max_length=120)
    # ENTEGRASYON_IZIN_KAPSAMLARI alt kümesi; en az bir kapsam zorunlu.
    izinler: list[str] = Field(min_length=1)
    gecerlilik_tarihi: datetime | None = None


class ApiAnahtariGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=120)
    aktif: bool | None = None


class ApiAnahtariCevapDTO(BaseModel):
    """``anahtar`` yalnız oluşturma yanıtında doludur (bir kez); listede hep ``None``."""

    id: int
    ad: str
    onek: str
    izinler: list[str]
    aktif: bool
    gecerlilik_tarihi: datetime | None
    son_kullanim_tarihi: datetime | None
    olusturma_tarihi: datetime
    anahtar: str | None = None


# --- Dış veri uçları (3. taraf ERP/muhasebe) ---


class StokBakiyeDTO(BaseModel):
    malzeme_id: int
    kod: str
    ad: str
    birim: str
    kategori: str
    mevcut_miktar: float
    kritik_stok: float
    kritik_altinda: bool


class SatinalmaKalemiDisDTO(BaseModel):
    malzeme_id: int
    miktar: float
    birim: str
    tahmini_birim_fiyat: float | None


class SatinalmaTalebiDisDTO(BaseModel):
    id: int
    kod: str
    baslik: str
    durum: str
    para_birimi: str
    onay_tarihi: datetime | None
    olusturma_tarihi: datetime
    kalemler: list[SatinalmaKalemiDisDTO]


class UretimOzetiSatirDTO(BaseModel):
    makine_id: int
    makine_kod: str
    toplam_adet: int
    saglam_adet: int
    fire_adet: int
    oee: float
    kullanilabilirlik: float
    performans: float
    kalite: float
