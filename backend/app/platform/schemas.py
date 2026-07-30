"""Platform API DTO'ları (Pydantic)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# --- Kimlik ---
class PlatformBenCevapDTO(BaseModel):
    id: int
    eposta: str
    ad_soyad: str
    son_giris_tarihi: datetime | None


# --- Tenant listesi/detayı ---
class TenantOzetDTO(BaseModel):
    id: int
    slug: str
    ad: str
    aktif: bool
    plan_kodu: str | None
    abonelik_durum: str | None
    koltuk_limiti: int | None
    koltuk_kullanilan: int | None
    olusturma_tarihi: datetime


class PlatformModulDurumDTO(BaseModel):
    kod: str
    ad: str
    acik: bool
    kaynak: str  # "plan" | "hak"


class PlatformOzellikDurumDTO(BaseModel):
    kod: str
    ad: str
    acik: bool
    deneysel: bool
    kaynak: str  # "plan" | "bayrak"


class TenantDetayDTO(BaseModel):
    id: int
    slug: str
    ad: str
    aktif: bool
    plan_kodu: str | None
    abonelik_durum: str | None
    abonelik_baslangic: datetime | None
    abonelik_bitis: datetime | None
    koltuk_limiti: int | None
    koltuk_kullanilan: int | None
    moduller: list[PlatformModulDurumDTO]
    ozellikler: list[PlatformOzellikDurumDTO]
    # S23: parola politikası / zorunlu 2FA / IP listesi / OIDC. OIDC istemci sırrı
    # MASKELİ döner (bkz. platform/guvenlik_ayar.py) — panel sırrı görüntülemez.
    guvenlik_ayarlari: dict[str, Any] | None = None
    olusturma_tarihi: datetime


# --- Tenant yaşam döngüsü ---
class TenantProvizyonDTO(BaseModel):
    slug: str = Field(min_length=1, max_length=63)
    ad: str = Field(min_length=1, max_length=200)
    plan_kodu: str = Field(min_length=1, max_length=50)
    admin_eposta: str = Field(min_length=3, max_length=255)
    admin_parola: str = Field(min_length=8, max_length=128)


class TenantGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=200)
    plan_kodu: str | None = Field(default=None, min_length=1, max_length=50)


class PlatformGuvenlikAyarDTO(BaseModel):
    """Tenant güvenlik ayarları yazma gövdesi (S23) — ``null`` = varsayılana dön.

    Beklenen biçim: ``{"parola": {"min_uzunluk": 12, "buyuk_kucuk": true, "rakam": true,
    "ozel_karakter": false}, "iki_asama_zorunlu": true, "ip_izin_listesi": ["10.0.0.0/8"]}``.
    """

    ayarlar: dict[str, Any] | None = None


class TenantSilDTO(BaseModel):
    # GitHub deseni: geri dönüşsüz silme için slug'ın birebir yazılması şarttır.
    onay: str = Field(min_length=1, max_length=63)


# --- Entitlement yazma ---
class HakAyarlaDTO(BaseModel):
    # None = override'ı kaldır (plana dön).
    acik: bool | None


# --- Abonelik listesi ---
class AbonelikSatirDTO(BaseModel):
    id: int
    tenant_id: int
    tenant_slug: str
    tenant_ad: str
    plan_kodu: str
    durum: str
    baslangic_tarihi: datetime
    bitis_tarihi: datetime | None


# --- Plan kataloğu ---
class PlanSatirDTO(BaseModel):
    kod: str
    ad: str
    koltuk_limiti: int | None
    moduller: list[str]
    ozellikler: list[str]


# --- Sağlık ---
class SondaDTO(BaseModel):
    durum: str  # "saglikli" | "hata"
    detay: str | None = None


class PlatformSaglikDTO(BaseModel):
    surum: str
    ortam: str
    veritabani: SondaDTO
    redis: SondaDTO
    nesne_depo: SondaDTO
    tenant_toplam: int
    tenant_aktif: int
    tenant_askida: int


# --- İhraç ---
class IhracCevapDTO(BaseModel):
    id: int
    tenant_id: int
    slug: str
    durum: str
    boyut: int | None
    tablo_sayisi: int | None
    hata: str | None
    olusturan_eposta: str | None
    olusturma_tarihi: datetime
