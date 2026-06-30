"""Deterministik PLC simülatörü — gerçek donanım olmadan uçtan uca akışı test eder.

Her ``oku()`` sayaçları tohumlu rastgelelikle ilerletir: çoğunlukla üretim, ara sıra
arıza (artış yok + duruş süresi birikir) ve düşük hız. Aynı tohum → aynı dizi.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime

from edge.paket import HamOkuma


class _MakineDurumu:
    def __init__(self) -> None:
        self.toplam = 0
        self.saglam = 0
        self.durus_dk = 0.0
        self.ideal_cevrim_sn = 30.0


class SimulasyonSurucu:
    """``makine_kodlari`` için sahte ama tutarlı sayaçlar üretir."""

    def __init__(self, makine_kodlari: list[str], *, tohum: int = 0) -> None:
        self._rng = random.Random(tohum)
        self._durumlar = {kod: _MakineDurumu() for kod in makine_kodlari}

    def oku(self) -> list[HamOkuma]:
        simdi = datetime.now(UTC)
        okumalar: list[HamOkuma] = []
        for kod, d in self._durumlar.items():
            ariza = self._rng.random() < 0.1
            if ariza:
                d.durus_dk += round(self._rng.uniform(0.5, 2.0), 2)
            else:
                uretilen = self._rng.randint(5, 20)
                hatali = self._rng.randint(0, max(1, uretilen // 10))
                d.toplam += uretilen
                d.saglam += uretilen - hatali
            okumalar.append(
                HamOkuma(
                    makine_kod=kod,
                    zaman=simdi,
                    toplam_sayac=d.toplam,
                    saglam_sayac=d.saglam,
                    durus_dk_sayac=d.durus_dk,
                    ideal_cevrim_sn=d.ideal_cevrim_sn,
                )
            )
        return okumalar
