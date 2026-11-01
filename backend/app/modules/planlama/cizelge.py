"""Sonlu kapasiteli çizelgeleme — saf (DB'siz), deterministik (S30, ADR-0049).

Her makine bağımsız bir tek-makine problemidir (iş emri makinesine zaten bağlı). Çalışılabilir
zaman yalnız vardiya pencereleridir; bir iş pencere sonunda kesilir, sonraki pencerede sürer.

**Sıralama kuralı.** Önce devam eden işler (başlamışı yarıda bırakmayız), sonra elle verilen sıra
(``elle_sira`` küçük önce), sonra en erken teslim tarihi (EDD), sonra öncelik (kritik → düşük),
sonra id. Tek makinede EDD en büyük gecikmeyi en aza indirir (Jackson, 1955); bu yüzden EDD
çizelgesinde teslimini kaçıran bir iş varsa, o makinede teslim tarihlerini **hiçbir sıra**
karşılayamaz: bu, kapasite aşımının deterministik tanımıdır (elle sıra verilmediyse). Elle sıra
verilmiş işler bu garantiyi bozabilir; o zaman gecikme "sıradan" mı "kapasiteden" mi diye ayrılır.

Aynı girdi her zaman aynı çizelgeyi verir (sıralama anahtarı tam sıralıdır, id son kırıcıdır).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta, tzinfo

ONCELIK_SIRASI = {"kritik": 0, "yuksek": 1, "orta": 2, "dusuk": 3}


@dataclass(frozen=True)
class Pencere:
    baslangic: datetime
    bitis: datetime

    @property
    def dakika(self) -> float:
        return (self.bitis - self.baslangic).total_seconds() / 60


@dataclass(frozen=True)
class Is:
    id: int
    sure_dk: float
    hedef: datetime | None = None
    oncelik: str = "orta"
    devam_ediyor: bool = False
    elle_sira: int | None = None


@dataclass
class Yerlesim:
    is_id: int
    parcalar: list[tuple[datetime, datetime]] = field(default_factory=list)
    gecikme_dk: float = 0.0

    @property
    def baslangic(self) -> datetime | None:
        return self.parcalar[0][0] if self.parcalar else None

    @property
    def bitis(self) -> datetime | None:
        return self.parcalar[-1][1] if self.parcalar else None


@dataclass
class Cizelge:
    yerlesimler: list[Yerlesim]
    sigmayan: list[int]  # ufukta bitirilemeyen işler (pencereler yetmedi)


def vardiya_pencereleri(
    vardiyalar: Iterable[tuple[time, time]],
    ilk_gun: date,
    gun_sayisi: int,
    saat_dilimi: tzinfo,
) -> list[Pencere]:
    """Vardiya saatlerinden ufuk boyunca çalışma pencereleri (gece vardiyası ertesi güne taşar).

    Çakışan ya da bitişik pencereler birleştirilir; sonuç başlangıca göre sıralıdır.
    """
    ham: list[Pencere] = []
    for g in range(gun_sayisi):
        gun = ilk_gun + timedelta(days=g)
        for bas, bit in vardiyalar:
            b = datetime.combine(gun, bas, saat_dilimi)
            e = datetime.combine(gun, bit, saat_dilimi)
            if e <= b:  # gece vardiyası: bitiş ertesi gün
                e += timedelta(days=1)
            ham.append(Pencere(b, e))
    ham.sort(key=lambda p: p.baslangic)
    birlesik: list[Pencere] = []
    for p in ham:
        if birlesik and p.baslangic <= birlesik[-1].bitis:
            son = birlesik[-1]
            birlesik[-1] = Pencere(son.baslangic, max(son.bitis, p.bitis))
        else:
            birlesik.append(p)
    return birlesik


def sirala(isler: Iterable[Is]) -> list[Is]:
    uzak = datetime.max.replace(tzinfo=None)

    def anahtar(i: Is) -> tuple[int, int, datetime, int, int]:
        hedef = i.hedef.astimezone(UTC).replace(tzinfo=None) if i.hedef else uzak
        return (
            0 if i.devam_ediyor else 1,
            i.elle_sira if i.elle_sira is not None else 1_000_000,
            hedef,
            ONCELIK_SIRASI.get(i.oncelik, 2),
            i.id,
        )

    return sorted(isler, key=anahtar)


def cizelgele(isler: Iterable[Is], pencereler: Sequence[Pencere], baslangic: datetime) -> Cizelge:
    """İşleri sırayla, ``baslangic``tan itibaren pencerelere doldurur (ileri çizelgeleme)."""
    yerlesimler: list[Yerlesim] = []
    sigmayan: list[int] = []
    pi = 0
    imlec = baslangic
    for is_ in sirala(isler):
        kalan = max(is_.sure_dk, 0.0)
        y = Yerlesim(is_.id)
        while kalan > 1e-9 and pi < len(pencereler):
            p = pencereler[pi]
            bas = max(imlec, p.baslangic)
            if bas >= p.bitis:
                pi += 1
                continue
            bos_dk = (p.bitis - bas).total_seconds() / 60
            kullan = min(kalan, bos_dk)
            bit = bas + timedelta(minutes=kullan)
            y.parcalar.append((bas, bit))
            kalan -= kullan
            imlec = bit
            if bit >= p.bitis:
                pi += 1
        if kalan > 1e-9:
            sigmayan.append(is_.id)
        if is_.hedef is not None and y.bitis is not None and kalan <= 1e-9:
            y.gecikme_dk = max((y.bitis - is_.hedef).total_seconds() / 60, 0.0)
        yerlesimler.append(y)
    return Cizelge(yerlesimler, sigmayan)


def gunluk_yuk(
    cizelge: Cizelge, pencereler: Sequence[Pencere], saat_dilimi: tzinfo
) -> dict[date, tuple[float, float]]:
    """Gün → (planlanan dakika, kapasite dakikası); gün sınırını aşan parça bölünür."""

    def dagit(bas: datetime, bit: datetime, hedef: dict[date, float]) -> None:
        b = bas.astimezone(saat_dilimi)
        e = bit.astimezone(saat_dilimi)
        while b < e:
            gun_sonu = datetime.combine(b.date() + timedelta(days=1), time(0), saat_dilimi)
            parca_son = min(e, gun_sonu)
            hedef[b.date()] = hedef.get(b.date(), 0.0) + (parca_son - b).total_seconds() / 60
            b = parca_son

    plan: dict[date, float] = {}
    kapasite: dict[date, float] = {}
    for p in pencereler:
        dagit(p.baslangic, p.bitis, kapasite)
    for y in cizelge.yerlesimler:
        for bas, bit in y.parcalar:
            dagit(bas, bit, plan)
    return {g: (round(plan.get(g, 0.0), 1), round(kapasite[g], 1)) for g in sorted(kapasite)}


def kapasite_asimi(isler: Sequence[Is], cizelge: Cizelge) -> list[int]:
    """Teslim tarihi hiçbir sırayla karşılanamayan işler.

    Elle sıra yoksa EDD çizelgesindeki gecikenlerdir (EDD en büyük gecikmeyi en aza indirir).
    Elle sıra varsa aynı işler sırasız (saf EDD) yeniden çizelgelenmeden bu ayrım yapılamaz;
    çağıran ``elle_sira`` olmadan ikinci kez çizelgeleyip bu fonksiyona onu verir.
    """
    geciken = {y.is_id for y in cizelge.yerlesimler if y.gecikme_dk > 0}
    return [i.id for i in isler if i.id in geciken or i.id in cizelge.sigmayan]
