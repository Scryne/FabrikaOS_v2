"""Analitik DTO'ları — modüller-arası KPI özeti + günlük üretim trendi."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class UretimKpiDTO(BaseModel):
    kayit_sayisi: int
    toplam_adet: int
    saglam_adet: int
    fire_orani: float
    kullanilabilirlik: float
    performans: float
    kalite: float
    oee: float


class MakineKpiDTO(BaseModel):
    toplam: int
    durumlar: dict[str, int]


class IsEmriKpiDTO(BaseModel):
    acik: int
    kapanan: int
    ortalama_kapanma_saat: float | None


class StokKpiDTO(BaseModel):
    toplam_malzeme: int
    kritik_sayisi: int


class KaliteKpiDTO(BaseModel):
    kontrol_sayisi: int
    gecme_orani: float | None
    acik_uygunsuzluk: int


class EnerjiKirilimDTO(BaseModel):
    enerji_turu: str
    birim: str
    toplam: float


class EnerjiKpiDTO(BaseModel):
    kirilim: list[EnerjiKirilimDTO]


class IsgKpiDTO(BaseModel):
    olay_sayisi: int
    kaza_sayisi: int


class BakimKpiDTO(BaseModel):
    aktif_plan: int
    geciken: int


class KpiCevapDTO(BaseModel):
    gun: int
    baslangic: datetime
    bitis: datetime
    uretim: UretimKpiDTO
    makine: MakineKpiDTO
    isemri: IsEmriKpiDTO
    stok: StokKpiDTO
    kalite: KaliteKpiDTO
    enerji: EnerjiKpiDTO
    isg: IsgKpiDTO
    bakim: BakimKpiDTO


class TrendNoktasiDTO(BaseModel):
    gun: date
    kayit_sayisi: int
    toplam_adet: int
    saglam_adet: int
    fire_orani: float
    oee: float
