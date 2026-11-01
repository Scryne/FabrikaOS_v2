"""Finans saf hesapları (S29, ADR-0048) — tutar, KDV, cari işareti, yaşlandırma. DB'siz.

Para Decimal ile ve 2 basamağa *satır başına* yuvarlanır (ROUND_HALF_UP, Türk faturalarındaki
genel uygulama): satır tutarı = miktar × birim fiyat, KDV = satır tutarı × oran / 100; toplamlar
yuvarlanmış satırların toplamıdır, böylece fatura üzerindeki her satır toplamla kuruşu kuruşuna
tutar.

**Cari işareti** firmanın bakiyesini *bizim* gözümüzden tutar: pozitif bakiye = firma bize borçlu
(alacağımız), negatif = biz firmaya borçluyuz.

| Hareket | Bakiye |
|---|---|
| Satış faturası kesildi | + genel toplam |
| Tahsilat (firmadan para geldi) | − tutar |
| Alış faturası kesildi | − genel toplam |
| Ödeme (firmaya para gitti) | + tutar |
| İptal | kesilmenin tersi |
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

KURUS = Decimal("0.01")
KDV_ORANLARI: frozenset[int] = frozenset({0, 1, 10, 20})
FATURA_TURLERI: frozenset[str] = frozenset({"satis", "alis"})
ODEME_TURLERI: frozenset[str] = frozenset({"tahsilat", "odeme"})
ODEME_YONTEMLERI: frozenset[str] = frozenset({"havale", "nakit", "kredi_karti", "cek", "senet"})
# Yaşlandırma kovaları (vadeden bu yana gün): vadesi gelmemiş, 0–30, 31–60, 61–90, 90+.
YASLANDIRMA_KOVALARI: tuple[str, ...] = ("vadesi_gelmemis", "0_30", "31_60", "61_90", "90_ustu")


def yuvarla(deger: Decimal) -> Decimal:
    return deger.quantize(KURUS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class KalemTutari:
    satir_tutari: Decimal
    kdv_tutari: Decimal


@dataclass(frozen=True)
class FaturaToplami:
    ara_toplam: Decimal
    kdv_toplam: Decimal
    genel_toplam: Decimal


def kalem_hesapla(miktar: Decimal, birim_fiyat: Decimal, kdv_orani: int) -> KalemTutari:
    if kdv_orani not in KDV_ORANLARI:
        raise ValueError(f"Geçersiz KDV oranı: {kdv_orani}")
    if miktar <= 0 or birim_fiyat < 0:
        raise ValueError("Miktar pozitif, birim fiyat negatif olmayan olmalı")
    satir = yuvarla(miktar * birim_fiyat)
    return KalemTutari(satir_tutari=satir, kdv_tutari=yuvarla(satir * kdv_orani / Decimal(100)))


def fatura_toplami(kalemler: Iterable[KalemTutari]) -> FaturaToplami:
    liste = list(kalemler)
    ara = sum((k.satir_tutari for k in liste), Decimal("0.00"))
    kdv = sum((k.kdv_tutari for k in liste), Decimal("0.00"))
    return FaturaToplami(ara_toplam=ara, kdv_toplam=kdv, genel_toplam=ara + kdv)


def fatura_cari_etkisi(tur: str, genel_toplam: Decimal) -> Decimal:
    """Kesilen faturanın firma bakiyesine etkisi (iptalde işareti ters çevrilir)."""
    if tur not in FATURA_TURLERI:
        raise ValueError(f"Geçersiz fatura türü: {tur}")
    return genel_toplam if tur == "satis" else -genel_toplam


def odeme_cari_etkisi(tur: str, tutar: Decimal) -> Decimal:
    if tur not in ODEME_TURLERI:
        raise ValueError(f"Geçersiz ödeme türü: {tur}")
    return -tutar if tur == "tahsilat" else tutar


def odeme_faturaya_uyar_mi(odeme_turu: str, fatura_turu: str) -> bool:
    """Tahsilat yalnız satış faturasına, ödeme yalnız alış faturasına bağlanır."""
    return (odeme_turu, fatura_turu) in {("tahsilat", "satis"), ("odeme", "alis")}


def acik_tutar(genel_toplam: Decimal, odenen: Decimal) -> Decimal:
    return max(genel_toplam - odenen, Decimal("0.00"))


def yaslandirma_kovasi(vade: date, bugun: date) -> str:
    gecen = (bugun - vade).days
    if gecen < 0:
        return "vadesi_gelmemis"
    if gecen <= 30:
        return "0_30"
    if gecen <= 60:
        return "31_60"
    if gecen <= 90:
        return "61_90"
    return "90_ustu"
