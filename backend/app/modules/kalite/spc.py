"""İstatistiksel proses kontrolü (S26, ADR-0025) — saf fonksiyonlar, veritabanı bilmez.

X̄-R kontrol kartı: alt grup ortalamaları (X̄) ve aralıkları (R). Limitler Shewhart sabitleriyle
(ASTM E2587 / Montgomery, *Introduction to Statistical Quality Control*, Ek VI):

    X̄ kartı: CL = X̿,  UCL/LCL = X̿ ± A2·R̄
    R kartı: CL = R̄,   UCL = D4·R̄,  LCL = D3·R̄

Kural ihlalleri Western Electric kurallarıdır (X̄ kartında; σ_X̄ = A2·R̄/3):
  1. Bir nokta 3σ dışında.
  2. Ardışık 3 noktanın 2'si aynı tarafta 2σ'nın ötesinde.
  3. Ardışık 5 noktanın 4'ü aynı tarafta 1σ'nın ötesinde.
  4. Ardışık 8 nokta merkez çizginin aynı tarafında.
R kartında yalnız kural 1 uygulanır. İhlal, deseni **tamamlayan** noktanın indeksine yazılır:
yeni bir ölçüm geldiğinde "bu nokta yeni bir ihlal doğurdu mu" sorusu tek indeksle cevaplanır.
Kural 2/3'te tamamlayan nokta kendisi de bölgenin ötesindedir (aynı desen iki kez sayılmaz).

Yetenek: σ_iç = R̄/d2; Cp = (ÜSL − ASL)/6σ, Cpk = min(ÜSL − X̿, X̿ − ASL)/3σ.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

# n → (A2, D3, D4, d2)
SABITLER: dict[int, tuple[float, float, float, float]] = {
    2: (1.880, 0.000, 3.267, 1.128),
    3: (1.023, 0.000, 2.574, 1.693),
    4: (0.729, 0.000, 2.282, 2.059),
    5: (0.577, 0.000, 2.114, 2.326),
    6: (0.483, 0.000, 2.004, 2.534),
    7: (0.419, 0.076, 1.924, 2.704),
    8: (0.373, 0.136, 1.864, 2.847),
    9: (0.337, 0.184, 1.816, 2.970),
    10: (0.308, 0.223, 1.777, 3.078),
}
EN_AZ_ALT_GRUP = 2  # limit hesabı için (anlamlı faz-I için ≥ 20 önerilir; ekranda uyarılır)
ONERILEN_ALT_GRUP = 20


class SpcHatasi(ValueError):
    pass


@dataclass(frozen=True)
class Limitler:
    n: int
    alt_grup_sayisi: int
    xbar_cl: float
    xbar_ucl: float
    xbar_lcl: float
    r_cl: float
    r_ucl: float
    r_lcl: float

    @property
    def sigma_xbar(self) -> float:
        return (self.xbar_ucl - self.xbar_cl) / 3


@dataclass(frozen=True)
class Ihlal:
    kart: str  # "xbar" | "r"
    kural: int
    indeks: int
    aciklama: str


KURAL_ACIKLAMALARI = {
    1: "Nokta kontrol limitlerinin dışında (3σ).",
    2: "Ardışık 3 noktanın 2'si aynı tarafta 2σ'nın ötesinde.",
    3: "Ardışık 5 noktanın 4'ü aynı tarafta 1σ'nın ötesinde.",
    4: "Ardışık 8 nokta merkez çizginin aynı tarafında.",
}


def ortalama(degerler: Sequence[float]) -> float:
    return sum(degerler) / len(degerler)


def aralik(degerler: Sequence[float]) -> float:
    return max(degerler) - min(degerler)


def _alt_grup_dogrula(alt_gruplar: Sequence[Sequence[float]]) -> int:
    if len(alt_gruplar) < EN_AZ_ALT_GRUP:
        raise SpcHatasi(f"Limit hesabı için en az {EN_AZ_ALT_GRUP} alt grup gerekli")
    boyutlar = {len(g) for g in alt_gruplar}
    if len(boyutlar) != 1:
        raise SpcHatasi("Alt grupların hepsi aynı boyutta olmalı")
    n = boyutlar.pop()
    if n not in SABITLER:
        raise SpcHatasi("Alt grup boyutu 2 ile 10 arasında olmalı (X̄-R kartı)")
    return n


def xbar_r_limitleri(alt_gruplar: Sequence[Sequence[float]]) -> Limitler:
    n = _alt_grup_dogrula(alt_gruplar)
    a2, d3, d4, _d2 = SABITLER[n]
    xbarlar = [ortalama(g) for g in alt_gruplar]
    rler = [aralik(g) for g in alt_gruplar]
    x_cift = ortalama(xbarlar)
    r_bar = ortalama(rler)
    return Limitler(
        n=n,
        alt_grup_sayisi=len(alt_gruplar),
        xbar_cl=x_cift,
        xbar_ucl=x_cift + a2 * r_bar,
        xbar_lcl=x_cift - a2 * r_bar,
        r_cl=r_bar,
        r_ucl=d4 * r_bar,
        r_lcl=d3 * r_bar,
    )


def western_electric(noktalar: Sequence[float], cl: float, sigma: float) -> list[Ihlal]:
    """X̄ noktalarında dört kuralı uygular. Aynı nokta birden çok kuralı tamamlayabilir."""
    ihlaller: list[Ihlal] = []
    if sigma <= 0:
        return ihlaller  # tüm alt gruplar aynı: bölge tanımsız, kural uygulanamaz

    def taraf(x: float) -> int:
        return 1 if x > cl else -1 if x < cl else 0

    def ekle(kural: int, i: int) -> None:
        ihlaller.append(Ihlal("xbar", kural, i, KURAL_ACIKLAMALARI[kural]))

    for i, x in enumerate(noktalar):
        if abs(x - cl) > 3 * sigma:
            ekle(1, i)
        if i >= 2:
            pencere = noktalar[i - 2 : i + 1]
            for yon in (1, -1):
                if (x - cl) * yon > 2 * sigma and sum(
                    1 for p in pencere if (p - cl) * yon > 2 * sigma
                ) >= 2:
                    ekle(2, i)
        if i >= 4:
            pencere = noktalar[i - 4 : i + 1]
            for yon in (1, -1):
                if (x - cl) * yon > sigma and sum(
                    1 for p in pencere if (p - cl) * yon > sigma
                ) >= 4:
                    ekle(3, i)
        if i >= 7:
            yonler = {taraf(p) for p in noktalar[i - 7 : i + 1]}
            if len(yonler) == 1 and 0 not in yonler:
                ekle(4, i)
    return ihlaller


def r_karti_ihlalleri(rler: Sequence[float], limitler: Limitler) -> list[Ihlal]:
    return [
        Ihlal("r", 1, i, KURAL_ACIKLAMALARI[1])
        for i, r in enumerate(rler)
        if r > limitler.r_ucl or r < limitler.r_lcl
    ]


@dataclass(frozen=True)
class Yetenek:
    sigma_ic: float
    cp: float | None
    cpk: float | None


def yetenek(
    limitler: Limitler,
    *,
    alt_tolerans: Decimal | float | None,
    ust_tolerans: Decimal | float | None,
) -> Yetenek | None:
    """Proses yeteneği; σ sıfırsa (aralıklar 0) ya da hiç tolerans yoksa None."""
    d2 = SABITLER[limitler.n][3]
    sigma = limitler.r_cl / d2
    if sigma <= 0 or (alt_tolerans is None and ust_tolerans is None):
        return None
    asl = float(alt_tolerans) if alt_tolerans is not None else None
    usl = float(ust_tolerans) if ust_tolerans is not None else None
    mu = limitler.xbar_cl
    cp = (usl - asl) / (6 * sigma) if asl is not None and usl is not None else None
    adaylar = []
    if usl is not None:
        adaylar.append((usl - mu) / (3 * sigma))
    if asl is not None:
        adaylar.append((mu - asl) / (3 * sigma))
    return Yetenek(sigma_ic=sigma, cp=cp, cpk=min(adaylar))
