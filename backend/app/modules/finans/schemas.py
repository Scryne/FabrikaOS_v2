"""Finans DTO'ları (S29, ADR-0048).

Girdi para alanları ``Decimal`` (ondalık basamak sınırıyla) alınır, hesap sunucuda Decimal ile
yapılır; yanıtta JSON sayısı (``float``) olarak döner. Kimlik alanları int64 sınırlıdır.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import AliasChoices, BaseModel, Field


class FaturaKalemiGirdiDTO(BaseModel):
    aciklama: str = Field(min_length=1, max_length=300)
    miktar: Decimal = Field(gt=0, le=Decimal("999999999"), decimal_places=3)
    birim: str = Field(default="adet", min_length=1, max_length=20)
    birim_fiyat: Decimal = Field(ge=0, le=Decimal("99999999999"), decimal_places=4)
    kdv_orani: int = Field(default=20)
    malzeme_id: int | None = Field(default=None, ge=1, le=2**63 - 1)


class FaturaOlusturDTO(BaseModel):
    tur: str = Field(pattern="^(satis|alis)$")
    firma_id: int = Field(ge=1, le=2**63 - 1)
    fatura_tarihi: date
    vade_gun: int = Field(default=30, ge=0, le=365)
    kalemler: list[FaturaKalemiGirdiDTO] = Field(min_length=1, max_length=200)
    aciklama: str = Field(default="", max_length=1000)
    senaryo: str = Field(default="TEMELFATURA", pattern="^(TEMELFATURA|TICARIFATURA|EARSIV)$")
    satinalma_siparisi_id: int | None = Field(default=None, ge=1, le=2**63 - 1)


class FaturaGuncelleDTO(BaseModel):
    firma_id: int | None = Field(default=None, ge=1, le=2**63 - 1)
    fatura_tarihi: date | None = None
    vade_gun: int | None = Field(default=None, ge=0, le=365)
    kalemler: list[FaturaKalemiGirdiDTO] | None = Field(default=None, min_length=1, max_length=200)
    aciklama: str | None = Field(default=None, max_length=1000)


class NedenDTO(BaseModel):
    # Onaylarım red düğmesi ``red_nedeni`` gönderir; ikisi de kabul edilir.
    neden: str = Field(
        default="", max_length=500, validation_alias=AliasChoices("neden", "red_nedeni")
    )


class FaturaKalemiCevapDTO(BaseModel):
    id: int
    sira: int
    aciklama: str
    malzeme_id: int | None
    miktar: float
    birim: str
    birim_fiyat: float
    kdv_orani: int
    satir_tutari: float
    kdv_tutari: float


class FaturaCevapDTO(BaseModel):
    id: int
    kod: str
    tur: str
    firma_id: int
    firma_ad: str
    durum: str
    fatura_tarihi: date
    vade_tarihi: date
    para_birimi: str
    ara_toplam: float
    kdv_toplam: float
    genel_toplam: float
    odenen_tutar: float
    acik_tutar: float
    vadesi_gecti: bool
    aciklama: str
    iade_nedeni: str
    iptal_nedeni: str
    satinalma_siparisi_id: int | None
    olusturan_kullanici_id: int | None
    kesen_kullanici_id: int | None
    kesim_tarihi: datetime | None
    ettn: str
    senaryo: str
    gib_durumu: str
    olusturma_tarihi: datetime
    kalemler: list[FaturaKalemiCevapDTO]


class OdemeOlusturDTO(BaseModel):
    tur: str = Field(pattern="^(tahsilat|odeme)$")
    firma_id: int = Field(ge=1, le=2**63 - 1)
    tutar: Decimal = Field(gt=0, le=Decimal("99999999999"), decimal_places=2)
    tarih: date
    yontem: str = Field(default="havale", max_length=20)
    fatura_id: int | None = Field(default=None, ge=1, le=2**63 - 1)
    aciklama: str = Field(default="", max_length=500)
    idempotency_anahtari: str | None = Field(default=None, min_length=8, max_length=80)


class OdemeCevapDTO(BaseModel):
    id: int
    kod: str
    tur: str
    firma_id: int
    firma_ad: str
    fatura_id: int | None
    fatura_kod: str | None
    tarih: date
    tutar: float
    yontem: str
    aciklama: str
    olusturma_tarihi: datetime


class CariHesapCevapDTO(BaseModel):
    firma_id: int
    firma_ad: str
    firma_tip: str
    bakiye: float
    para_birimi: str
    acik_fatura: int
    vadesi_gecen: float
    son_hareket: date | None


class CariHareketCevapDTO(BaseModel):
    id: int
    tarih: date
    tur: str
    aciklama: str
    borc: float  # firmayı borçlandıran (bakiye artışı)
    alacak: float  # firmayı alacaklandıran (bakiye azalışı)
    bakiye_sonrasi: float
    kaynak: str


class CariEkstreDTO(BaseModel):
    firma_id: int
    firma_ad: str
    bakiye: float
    acilis_bakiyesi: float
    hareketler: list[CariHareketCevapDTO]


class FinansOzetDTO(BaseModel):
    acik_alacak: float
    acik_borc: float
    vadesi_gecen_alacak: float
    bu_ay_satis: float
    bu_ay_tahsilat: float
    onay_bekleyen: int


class YaslandirmaFirmaDTO(BaseModel):
    firma_id: int
    firma_ad: str
    toplam: float
    vadesi_gelmemis: float
    gun_0_30: float
    gun_31_60: float
    gun_61_90: float
    gun_90_ustu: float


class YaslandirmaYonuDTO(BaseModel):
    toplam: float
    vadesi_gelmemis: float
    gun_0_30: float
    gun_31_60: float
    gun_61_90: float
    gun_90_ustu: float
    firmalar: list[YaslandirmaFirmaDTO]


class YaslandirmaDTO(BaseModel):
    alacak: YaslandirmaYonuDTO
    borc: YaslandirmaYonuDTO


class MaliyetKalemiDTO(BaseModel):
    malzeme_id: int
    malzeme_kod: str
    malzeme_ad: str
    miktar: float
    birim_fiyat: float | None
    fiyat_kaynagi: str
    tutar: float | None


class IsEmriMaliyetiDTO(BaseModel):
    is_emri_id: int
    is_emri_kod: str
    urun_kod: str
    urun_ad: str
    miktar: float | None
    kapanis_tarihi: datetime | None
    malzeme_maliyeti: float
    birim_maliyet: float | None
    eksik_fiyat: int
    kalemler: list[MaliyetKalemiDTO]


class GibDurumDTO(BaseModel):
    gib_durumu: str = Field(pattern="^(gonderildi|kabul|red|hata)$")


class EFaturaDisDTO(BaseModel):
    """e-Fatura entegratörüne giden alanlar (UBL-TR'yi entegratör üretir; bu iskelet veridir)."""

    ettn: str
    kod: str
    tur: str
    senaryo: str
    fatura_tarihi: date
    para_birimi: str
    gonderen: str
    karsi_taraf_unvan: str
    karsi_taraf_vkn: str
    karsi_taraf_vergi_dairesi: str
    ara_toplam: float
    kdv_toplam: float
    genel_toplam: float
    gib_durumu: str
    kalemler: list[FaturaKalemiCevapDTO]
