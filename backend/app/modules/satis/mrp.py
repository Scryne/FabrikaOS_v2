"""Malzeme ihtiyaç planlama — saf (DB'siz), deterministik (S31, ADR-0050).

Bir siparişin kalemleri (ürün × miktar) tek seviyeli reçeteyle (S24 BOM) malzemeye patlatılır.
Her malzeme için:

    brüt       = Σ kalem miktarı × reçete birim tüketimi
    kullanılabilir = eldeki stok + açık tedarik − ayrılmış
    net        = max(0, brüt − kullanılabilir)

**Açık tedarik:** henüz stoğa girmemiş ama gelecek miktar — siparişe dönmemiş açık satınalma
talepleri + açık satınalma siparişlerinin teslim alınmamış kısmı. **Ayrılmış:** açık iş emirlerinin
reçetesi henüz stoktan düşülmemiş tüketimi (iş emri kapanırken BOM düşer, S24). Bu iki terim
olmadan aynı malzeme iki siparişe birden "yeterli" görünür ya da gelmekte olan malzeme için ikinci
talep açılır.

Reçetesi olmayan ürün patlatılamaz; `recetesiz` listesinde döner (sessizce 0 sayılmaz).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal

SIFIR = Decimal(0)


@dataclass(frozen=True)
class Kalem:
    urun_id: int
    miktar: Decimal


@dataclass(frozen=True)
class MalzemeIhtiyaci:
    malzeme_id: int
    brut: Decimal
    eldeki: Decimal
    acik_tedarik: Decimal
    ayrilmis: Decimal

    @property
    def kullanilabilir(self) -> Decimal:
        return self.eldeki + self.acik_tedarik - self.ayrilmis

    @property
    def net(self) -> Decimal:
        return max(SIFIR, self.brut - self.kullanilabilir)


@dataclass(frozen=True)
class MrpSonucu:
    ihtiyaclar: list[MalzemeIhtiyaci]  # malzeme_id'ye göre sıralı
    recetesiz: list[int]  # reçetesi olmayan ürün id'leri (sıralı, tekil)

    @property
    def eksikler(self) -> list[MalzemeIhtiyaci]:
        return [i for i in self.ihtiyaclar if i.net > 0]


def brut_ihtiyac(
    kalemler: Iterable[Kalem], receteler: Mapping[int, Sequence[tuple[int, Decimal]]]
) -> tuple[dict[int, Decimal], list[int]]:
    """Kalemleri reçeteyle malzemeye patlatır: {malzeme_id: brüt}, reçetesiz ürünler."""
    brut: dict[int, Decimal] = {}
    recetesiz: set[int] = set()
    for k in kalemler:
        satirlar = receteler.get(k.urun_id)
        if not satirlar:
            recetesiz.add(k.urun_id)
            continue
        for malzeme_id, birim_tuketim in satirlar:
            brut[malzeme_id] = brut.get(malzeme_id, SIFIR) + k.miktar * birim_tuketim
    return brut, sorted(recetesiz)


def hesapla(
    kalemler: Iterable[Kalem],
    receteler: Mapping[int, Sequence[tuple[int, Decimal]]],
    eldeki: Mapping[int, Decimal],
    acik_tedarik: Mapping[int, Decimal],
    ayrilmis: Mapping[int, Decimal],
) -> MrpSonucu:
    brut, recetesiz = brut_ihtiyac(kalemler, receteler)
    ihtiyaclar = [
        MalzemeIhtiyaci(
            malzeme_id=m,
            brut=brut[m],
            eldeki=eldeki.get(m, SIFIR),
            acik_tedarik=acik_tedarik.get(m, SIFIR),
            ayrilmis=ayrilmis.get(m, SIFIR),
        )
        for m in sorted(brut)
    ]
    return MrpSonucu(ihtiyaclar=ihtiyaclar, recetesiz=recetesiz)
