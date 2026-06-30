"""Saha modülü Pydantic DTO'ları + ölçüm kontratı (OlcumPaketi).

``OlcumPaketi`` edge ajanı, MQTT ingestion'ı ve REST/CSV uçlarının paylaştığı tek
sözleşmedir. Edge ajanı (``edge/paket.py``) aynı JSON şeklini bağımsız üretir; uçtan
uca uyum bir kontrat testiyle güvenceye alınır.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# Desteklenen saha protokolleri (MVP'de yalnız simülasyon yazar; opcua/modbus iskelet).
PROTOKOLLER = frozenset({"simulasyon", "opcua", "modbus"})


class OlcumPaketi(BaseModel):
    """Bir makinenin tek aralık üretim özeti (UretimVerisi şekli + idempotency kimliği)."""

    olcum_id: UUID
    makine_kod: str = Field(min_length=1, max_length=50)
    zaman: datetime
    vardiya: str | None = Field(default=None, max_length=20)
    planlanan_sure_dk: float = Field(ge=0)
    durus_sure_dk: float = Field(ge=0)
    toplam_adet: int = Field(ge=0)
    saglam_adet: int = Field(ge=0)
    ideal_cevrim_sn: float = Field(ge=0)

    @model_validator(mode="after")
    def _saglam_kontrol(self) -> OlcumPaketi:
        if self.saglam_adet > self.toplam_adet:
            raise ValueError("saglam_adet toplam_adet'i aşamaz")
        return self


class CihazOlusturDTO(BaseModel):
    kod: str = Field(min_length=1, max_length=50)
    ad: str = Field(min_length=1, max_length=200)
    protokol: str = Field(default="simulasyon")

    @model_validator(mode="after")
    def _protokol_kontrol(self) -> CihazOlusturDTO:
        if self.protokol not in PROTOKOLLER:
            raise ValueError(f"Geçersiz protokol: {self.protokol!r}")
        return self


class CihazCevapDTO(BaseModel):
    id: int
    kod: str
    ad: str
    protokol: str
    aktif: bool
    son_gorulme: datetime | None = None


class OlcumKabulDTO(BaseModel):
    """REST toplu ingestion gövdesi: bir gateway'in bir veya çok ölçümü."""

    cihaz_kod: str = Field(min_length=1, max_length=50)
    olcumler: list[OlcumPaketi] = Field(min_length=1)
