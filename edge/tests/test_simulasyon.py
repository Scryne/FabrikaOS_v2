"""Edge simülasyon sürücüsü: determinizm + monoton artan sayaçlar."""

from __future__ import annotations

from edge.suruculer.simulasyon import SimulasyonSurucu


def test_determinizm_ayni_tohum() -> None:
    a = SimulasyonSurucu(["MAK-1", "MAK-2"], tohum=42)
    b = SimulasyonSurucu(["MAK-1", "MAK-2"], tohum=42)
    for _ in range(5):
        oa = {h.makine_kod: h for h in a.oku()}
        ob = {h.makine_kod: h for h in b.oku()}
        assert oa["MAK-1"].toplam_sayac == ob["MAK-1"].toplam_sayac


def test_sayaclar_monoton_artar() -> None:
    s = SimulasyonSurucu(["MAK-1"], tohum=1)
    onceki = 0
    for _ in range(10):
        v = s.oku()[0].toplam_sayac
        assert v >= onceki
        onceki = v


def test_saglam_toplami_asmaz() -> None:
    s = SimulasyonSurucu(["MAK-1"], tohum=7)
    for _ in range(20):
        h = s.oku()[0]
        assert h.saglam_sayac <= h.toplam_sayac
