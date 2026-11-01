"""Emisyon hesabı — saf (DB'siz), deterministik (S32, ADR-0051).

    emisyon (kg CO2e) = tüketim (birim) × faktör (kg CO2e / birim)

Faktör enerji türü + birim çiftine ve tarihe göre seçilir: dönemin ilk gününde geçerli olan en
yeni faktör (``gecerlilik <= gün``). Faktörü olmayan ya da birimi uyuşmayan tüketim **0 sayılmaz**:
``faktorsuz`` listesinde miktarıyla döner (eksik veri sessizce "düşük emisyon" görünmesin).

Kapsamlar GHG Protocol'e göre: Kapsam 1 tesiste yakılan yakıt (doğalgaz), Kapsam 2 satın alınan
enerji (şebeke elektriği). Basınçlı hava ve su gibi elektrikle üretilen akışlara faktör verilmez:
onların enerjisi elektrik tüketiminin içindedir, ayrıca sayılırsa çift sayım olur.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

SIFIR = Decimal(0)
KAPSAMLAR = ("kapsam1", "kapsam2")

# Birim yazımları tek biçime: (normal birim, çarpan). Ham tabloda birim serbest metin.
_BIRIM: dict[str, tuple[str, Decimal]] = {
    "kwh": ("kwh", Decimal(1)),
    "mwh": ("kwh", Decimal(1000)),
    "m3": ("m3", Decimal(1)),
    "m³": ("m3", Decimal(1)),
    "sm3": ("m3", Decimal(1)),
    "nm3": ("m3", Decimal(1)),
}


def birim_normalle(birim: str, miktar: Decimal) -> tuple[str, Decimal]:
    """``("MWh", 2)`` → ``("kwh", 2000)``; tanınmayan birim küçük harfe iner, miktar değişmez."""
    anahtar = birim.strip().lower()
    if anahtar in _BIRIM:
        hedef, carpan = _BIRIM[anahtar]
        return hedef, miktar * carpan
    return anahtar, miktar


@dataclass(frozen=True)
class Faktor:
    enerji_turu: str
    birim: str  # normalleştirilmiş (kwh, m3)
    deger: Decimal  # kg CO2e / birim
    kapsam: str  # kapsam1 | kapsam2
    gecerlilik: date
    kaynak: str = ""


@dataclass(frozen=True)
class Tuketim:
    donem: date  # dönemin ilk günü (gün ya da ay başı)
    enerji_turu: str
    birim: str
    miktar: Decimal


@dataclass
class DonemSonucu:
    donem: date
    kapsam1: Decimal = SIFIR
    kapsam2: Decimal = SIFIR
    elektrik_kwh: Decimal = SIFIR

    @property
    def toplam(self) -> Decimal:
        return self.kapsam1 + self.kapsam2


@dataclass
class TurSonucu:
    enerji_turu: str
    birim: str
    miktar: Decimal = SIFIR
    emisyon: Decimal = SIFIR
    faktor: Faktor | None = None  # en son kullanılan (dönemler arası değişebilir)


@dataclass
class Sonuc:
    donemler: list[DonemSonucu]
    turler: list[TurSonucu]
    faktorsuz: list[TurSonucu] = field(default_factory=list)

    @property
    def kapsam1(self) -> Decimal:
        return sum((d.kapsam1 for d in self.donemler), SIFIR)

    @property
    def kapsam2(self) -> Decimal:
        return sum((d.kapsam2 for d in self.donemler), SIFIR)

    @property
    def toplam(self) -> Decimal:
        return self.kapsam1 + self.kapsam2


def faktor_sec(
    faktorler: Sequence[Faktor], enerji_turu: str, birim: str, gun: date
) -> Faktor | None:
    adaylar = [
        f
        for f in faktorler
        if f.enerji_turu == enerji_turu and f.birim == birim and f.gecerlilik <= gun
    ]
    return max(adaylar, key=lambda f: f.gecerlilik) if adaylar else None


def hesapla(tuketimler: Iterable[Tuketim], faktorler: Sequence[Faktor]) -> Sonuc:
    donemler: dict[date, DonemSonucu] = {}
    turler: dict[tuple[str, str], TurSonucu] = {}
    faktorsuz: dict[tuple[str, str], TurSonucu] = {}
    for t in tuketimler:
        birim, miktar = birim_normalle(t.birim, t.miktar)
        d = donemler.setdefault(t.donem, DonemSonucu(t.donem))
        if t.enerji_turu == "elektrik" and birim == "kwh":
            d.elektrik_kwh += miktar
        f = faktor_sec(faktorler, t.enerji_turu, birim, t.donem)
        if f is None:
            fs = faktorsuz.setdefault((t.enerji_turu, birim), TurSonucu(t.enerji_turu, birim))
            fs.miktar += miktar
            continue
        kg = miktar * f.deger
        if f.kapsam == "kapsam1":
            d.kapsam1 += kg
        else:
            d.kapsam2 += kg
        ts = turler.setdefault((t.enerji_turu, birim), TurSonucu(t.enerji_turu, birim))
        ts.miktar += miktar
        ts.emisyon += kg
        ts.faktor = f
    return Sonuc(
        donemler=[donemler[k] for k in sorted(donemler)],
        turler=[turler[k] for k in sorted(turler)],
        faktorsuz=[faktorsuz[k] for k in sorted(faktorsuz)],
    )


def yogunluk(pay: Decimal, adet: int) -> Decimal | None:
    """Birim ürün başına değer (kg CO2e/adet, kWh/adet); üretim yoksa tanımsız (None), 0 değil."""
    return pay / adet if adet > 0 else None
