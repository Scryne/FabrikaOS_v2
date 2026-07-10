"""Kimlik modülü Pydantic DTO'ları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TokenCevapDTO(BaseModel):
    access_token: str
    refresh_token: str
    token_tipi: str = "bearer"


class YenileGirdiDTO(BaseModel):
    refresh_token: str


class CikisGirdiDTO(BaseModel):
    refresh_token: str


class ParolaDegistirDTO(BaseModel):
    eski_parola: str = Field(min_length=1)
    yeni_parola: str = Field(min_length=8, max_length=128)


class BenCevapDTO(BaseModel):
    id: int
    eposta: str
    ad_soyad: str
    roller: list[str]
    izinler: list[str]
    son_giris_tarihi: datetime | None = None


class KullaniciOlusturDTO(BaseModel):
    eposta: str = Field(min_length=3, max_length=255)
    parola: str = Field(min_length=8, max_length=128)
    ad_soyad: str = Field(default="", max_length=200)
    roller: list[str] = Field(default_factory=list)
    # Dış portal (S18): dis-panel kullanıcısını CRM firmasına bağlar; iç kullanıcıda None.
    firma_id: int | None = None


class KullaniciCevapDTO(BaseModel):
    id: int
    eposta: str
    ad_soyad: str
    aktif: bool
    roller: list[str]
    firma_id: int | None = None


class RolCevapDTO(BaseModel):
    id: int
    ad: str
    aciklama: str
    izinler: list[str]


class RolSayiDTO(BaseModel):
    ad: str
    adet: int


class KullaniciOzetDTO(BaseModel):
    """Kullanıcı KPI özeti (OzetSerit) — salt-okunur toplulaştırma."""

    toplam: int
    aktif: int
    pasif: int
    rol_sayisi: int
    rol_dagilimi: list[RolSayiDTO]  # en kalabalık roller
