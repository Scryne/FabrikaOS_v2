"""Üretim modülü Pydantic DTO'ları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MakineOlusturDTO(BaseModel):
    kod: str = Field(min_length=1, max_length=50)
    ad: str = Field(min_length=1, max_length=200)
    oee_hedefi: float | None = Field(default=None, ge=0, le=1)
    # Coğrafi site haritası (S-VB): opsiyonel; koordinatsız makine yalnız SVG şemada.
    enlem: float | None = Field(default=None, ge=-90, le=90)
    boylam: float | None = Field(default=None, ge=-180, le=180)


class MakineGuncelleDTO(BaseModel):
    """Kısmi güncelleme; ``enlem``/``boylam`` null gönderilerek koordinat silinebilir."""

    ad: str | None = Field(default=None, min_length=1, max_length=200)
    oee_hedefi: float | None = Field(default=None, ge=0, le=1)
    enlem: float | None = Field(default=None, ge=-90, le=90)
    boylam: float | None = Field(default=None, ge=-180, le=180)


class MakineDurumDTO(BaseModel):
    durum: str = Field(min_length=1, max_length=20)


class MakineCevapDTO(BaseModel):
    id: int
    kod: str
    ad: str
    durum: str
    oee_hedefi: float | None = None
    enlem: float | None = None
    boylam: float | None = None


class UretimGirisDTO(BaseModel):
    makine_id: int
    zaman: datetime | None = None
    vardiya: str | None = Field(default=None, max_length=20)
    planlanan_sure_dk: float = Field(ge=0)
    durus_sure_dk: float = Field(ge=0)
    toplam_adet: int = Field(ge=0)
    saglam_adet: int = Field(ge=0)
    ideal_cevrim_sn: float = Field(ge=0)


class UretimVerisiCevapDTO(BaseModel):
    id: int
    makine_id: int
    zaman: datetime
    vardiya: str | None = None
    planlanan_sure_dk: float
    durus_sure_dk: float
    toplam_adet: int
    saglam_adet: int
    ideal_cevrim_sn: float


class OeeCevapDTO(BaseModel):
    makine_id: int
    kullanilabilirlik: float
    performans: float
    kalite: float
    oee: float
    kayit_sayisi: int


class OeeOzetSatirDTO(BaseModel):
    makine_id: int
    makine_kod: str
    kullanilabilirlik: float
    performans: float
    kalite: float
    oee: float
    kayit_sayisi: int


class DurumSayiDTO(BaseModel):
    durum: str
    adet: int


class UretimOzetDTO(BaseModel):
    """Üretim modülü KPI özeti (pano/OzetSerit) — salt-okunur toplulaştırma."""

    toplam_makine: int
    calisan: int
    durdu: int
    bakimda: int
    arizali: int
    uretimli_makine: int
    ortalama_oee: float  # 0–1 (frontend ×100 gösterir; filoOrtalamalari deseni)
    durum_dagilimi: list[DurumSayiDTO]
