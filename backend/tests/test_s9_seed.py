"""S9 seed: depo + satinalma-onaylayan rollerinin izin kümeleri (görev ayrımı)."""

from __future__ import annotations

from app.kimlik.izinler import VARSAYILAN_ROLLER


def test_depo_rolu_onaylayamaz() -> None:
    depo = VARSAYILAN_ROLLER["depo"]
    assert {"stok:oku", "stok:yaz", "satinalma:oku", "satinalma:yaz"} <= depo
    assert "satinalma:onay" not in depo


def test_onaylayan_rolu_yalniz_onay() -> None:
    rol = VARSAYILAN_ROLLER["satinalma-onaylayan"]
    assert frozenset({"satinalma:oku", "satinalma:onay"}) == rol
