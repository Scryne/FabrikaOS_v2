"""Rapor DTO'ları. ``nesne_anahtari`` bilinçli olarak yanıtta yoktur (depolama iç detayı)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RaporOlusturDTO(BaseModel):
    tur: str = Field(description="Rapor türü (uretim/stok/kalite/enerji/isemri)")
    bicim: str = Field(default="pdf", description="Çıktı biçimi (pdf/xlsx)")
    gun: int = Field(default=30, ge=1, le=365, description="Geriye dönük pencere (gün)")


class RaporCevapDTO(BaseModel):
    id: int
    kod: str
    tur: str
    bicim: str
    durum: str
    parametreler: dict[str, Any] | None
    dosya_adi: str
    icerik_tipi: str
    boyut: int
    satir_sayisi: int
    hata: str
    uretim_suresi_sn: float | None
    olusturan_kullanici_id: int | None
    olusturma_tarihi: datetime
