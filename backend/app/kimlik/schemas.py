"""Kimlik modülü Pydantic DTO'ları."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TokenCevapDTO(BaseModel):
    """Giriş cevabı — 2FA aktifse token'lar boş, ``gecici_token`` ile ikinci adım gerekir.

    ``iki_asama_kurulum_gerekli``: tenant 2FA'yı zorunlu kılmış ama kullanıcı kurulmamış —
    ``gecici_token`` yalnız 2FA kurulum uçlarında geçer (S23 / ADR-0022).
    """

    access_token: str = ""
    refresh_token: str = ""
    token_tipi: str = "bearer"
    iki_asama_gerekli: bool = False
    iki_asama_kurulum_gerekli: bool = False
    gecici_token: str = ""


class IkiAsamaDogrulaDTO(BaseModel):
    gecici_token: str = Field(min_length=1)
    kod: str = Field(min_length=6, max_length=12)  # TOTP (6) veya kurtarma kodu (XXXX-XXXX)


class IkiAsamaKurCevapDTO(BaseModel):
    """Kurulum başlangıcı — sır + QR URI'si (FE antd QRCode ile çizer)."""

    sir: str
    otpauth_uri: str


class IkiAsamaEtkinlestirDTO(BaseModel):
    kod: str = Field(min_length=6, max_length=8)


class IkiAsamaKurtarmaCevapDTO(BaseModel):
    """Kurtarma kodları — YALNIZ bu yanıtta görünür, sonra yalnız özet saklanır."""

    kurtarma_kodlari: list[str]


class IkiAsamaKapatDTO(BaseModel):
    parola: str = Field(min_length=1)
    kod: str = Field(min_length=6, max_length=12)


class SsoDurumCevapDTO(BaseModel):
    """Giriş ekranı SSO düğmesini göstersin mi (kimlik gerektirmez, sır sızdırmaz)."""

    aktif: bool


class SsoBaslatCevapDTO(BaseModel):
    """Tarayıcının yönlendirileceği IdP yetkilendirme URL'i (state + PKCE gömülü)."""

    yetkilendirme_url: str


class SsoTamamlaDTO(BaseModel):
    kod: str = Field(min_length=1, max_length=4096)
    state: str = Field(min_length=1, max_length=512)


class OturumCevapDTO(BaseModel):
    """Aktif oturum/cihaz satırı (S23) — jti sızdırılmaz, yalnız id ile yönetilir."""

    id: int
    ip_adresi: str | None = None
    istemci: str
    olusturma_tarihi: datetime
    son_kullanim: datetime | None = None
    bitis: datetime


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
    iki_asama_aktif: bool = False


class KullaniciOlusturDTO(BaseModel):
    eposta: str = Field(min_length=3, max_length=255)
    parola: str = Field(min_length=8, max_length=128)
    ad_soyad: str = Field(default="", max_length=200)
    roller: list[str] = Field(default_factory=list)
    # Dış portal (S18): dis-panel kullanıcısını CRM firmasına bağlar; iç kullanıcıda None.
    firma_id: int | None = None


class KullaniciGuncelleDTO(BaseModel):
    """Kısmi güncelleme — yalnız gönderilen alanlar işlenir (``exclude_unset``).

    ``firma_id`` açıkça ``null`` gönderilerek firma bağlantısı kaldırılabilir;
    ``aktif=false`` koltuk açar, ``aktif=true`` koltuk limitine tabidir.
    """

    ad_soyad: str | None = Field(default=None, max_length=200)
    aktif: bool | None = None
    roller: list[str] | None = None
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
