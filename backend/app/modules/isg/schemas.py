"""İSG modülü Pydantic DTO'ları (iş kazası + risk değerlendirme).

Risk değerlendirmede ``risk_skoru``/``risk_seviyesi`` yalnız **cevap** alanlarıdır; sunucu
``risk_matrisi`` ile hesaplar (istekte alınmaz → istemciye güvenilmez).
"""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class IsKazasiOlusturDTO(BaseModel):
    tur: str = Field(default="kaza", max_length=20)
    olay_tarihi: datetime | None = None
    yer: str = Field(default="", max_length=200)
    aciklama: str = Field(default="", max_length=2000)
    agirlik: str = Field(default="hafif", max_length=20)
    kaybedilen_gun: int = Field(default=0, ge=0)
    yaralanma_turu: str = Field(default="", max_length=200)
    personel_id: int | None = None
    makine_id: int | None = None


class IsKazasiGuncelleDTO(BaseModel):
    yer: str | None = Field(default=None, max_length=200)
    aciklama: str | None = Field(default=None, max_length=2000)
    agirlik: str | None = Field(default=None, max_length=20)
    kaybedilen_gun: int | None = Field(default=None, ge=0)
    yaralanma_turu: str | None = Field(default=None, max_length=200)
    personel_id: int | None = None
    makine_id: int | None = None


class IsKazasiCevapDTO(BaseModel):
    id: int
    kod: str
    tur: str
    olay_tarihi: datetime
    yer: str
    aciklama: str
    agirlik: str
    kaybedilen_gun: int
    yaralanma_turu: str
    personel_id: int | None = None
    makine_id: int | None = None
    raporlayan_kullanici_id: int | None = None
    olusturma_tarihi: datetime


class RiskDegerlendirmeOlusturDTO(BaseModel):
    baslik: str = Field(min_length=1, max_length=200)
    bolum: str = Field(default="", max_length=200)
    tehlike: str = Field(default="", max_length=2000)
    olasilik: int = Field(ge=1, le=5)
    siddet: int = Field(ge=1, le=5)
    onlem: str = Field(default="", max_length=2000)
    durum: str = Field(default="acik", max_length=20)
    sorumlu_kullanici_id: int | None = None
    gecerlilik_tarihi: date | None = None


class RiskDegerlendirmeGuncelleDTO(BaseModel):
    baslik: str | None = Field(default=None, max_length=200)
    bolum: str | None = Field(default=None, max_length=200)
    tehlike: str | None = Field(default=None, max_length=2000)
    olasilik: int | None = Field(default=None, ge=1, le=5)
    siddet: int | None = Field(default=None, ge=1, le=5)
    onlem: str | None = Field(default=None, max_length=2000)
    durum: str | None = Field(default=None, max_length=20)
    sorumlu_kullanici_id: int | None = None
    gecerlilik_tarihi: date | None = None


class RiskDegerlendirmeCevapDTO(BaseModel):
    id: int
    kod: str
    baslik: str
    bolum: str
    tehlike: str
    olasilik: int
    siddet: int
    risk_skoru: int
    risk_seviyesi: str
    onlem: str
    durum: str
    sorumlu_kullanici_id: int | None = None
    degerlendirme_tarihi: datetime
    gecerlilik_tarihi: date | None = None
    olusturma_tarihi: datetime


class RiskHucreDTO(BaseModel):
    olasilik: int
    siddet: int
    adet: int


class IsgOzetDTO(BaseModel):
    """İSG KPI özeti (İş kazaları + Risk ekranları) — salt-okunur toplulaştırma."""

    gunluk_kazasiz: int  # son kazadan bu yana gün (-1: hiç kaza yok)
    bu_yil_kaza: int
    ramak_kala: int
    toplam_kayip_gun: int
    acik_risk: int
    yuksek_risk: int
    toplam_risk: int
    risk_matrisi: list[RiskHucreDTO]  # 5×5 hücre sayaçları
