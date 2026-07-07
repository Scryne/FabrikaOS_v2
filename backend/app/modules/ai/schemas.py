"""AI modülü DTO'ları (Pydantic).

``nesne_anahtari`` yanıtlara **çıkmaz** (S12 belge deseni: depolama iç detayı dışarı
sızmaz). Tahmin sonuçları model türüne göre değişen serbest şemalı listelerdir
(``sonuclar``); alan sözleşmeleri ``modeller.py`` tahmin fonksiyonlarında sabittir.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class EgitimIstekDTO(BaseModel):
    tur: str = Field(min_length=1, max_length=30, description="Model türü")


class ModelKaydiCevapDTO(BaseModel):
    id: int
    tur: str
    surum: int
    durum: str
    aktif: bool
    metrikler: dict[str, Any] | None = None
    veri_ozeti: dict[str, Any] | None = None
    hata: str = ""
    egitim_suresi_sn: float | None = None
    olusturan_kullanici_id: int | None = None
    olusturma_tarihi: datetime


class TahminCevapDTO(BaseModel):
    """Bir çıkarım koşusunun yanıtı: kullanılan model + sonuç listesi."""

    tahmin_id: int
    tur: str
    model_id: int
    model_surum: int
    sonuclar: list[dict[str, Any]]
    veri_ozeti: dict[str, Any] | None = None
    zaman: datetime


class TahminGecmisCevapDTO(BaseModel):
    """Tahmin geçmişi satırı (listede sonuçların kendisi değil sayısı döner)."""

    id: int
    tur: str
    model_id: int
    sonuc_sayisi: int
    veri_ozeti: dict[str, Any] | None = None
    olusturma_tarihi: datetime
