"""S11 seed: İSG/İK rollerinin izin kümeleri + ik:onay görev ayrımı."""

from __future__ import annotations

from app.kimlik.izinler import IZIN_KATALOGU, VARSAYILAN_ROLLER


def test_isg_ik_izinleri_katalogda() -> None:
    for kod in ("isg:oku", "isg:yaz", "ik:oku", "ik:yaz", "ik:onay"):
        assert kod in IZIN_KATALOGU


def test_isg_rolu() -> None:
    assert VARSAYILAN_ROLLER["isg"] == frozenset({"isg:oku", "isg:yaz"})


def test_ik_rolu_onaylayamaz() -> None:
    ik = VARSAYILAN_ROLLER["ik"]
    assert {"ik:oku", "ik:yaz"} <= ik
    assert "ik:onay" not in ik


def test_ik_onaylayan_rolu() -> None:
    assert VARSAYILAN_ROLLER["ik-onaylayan"] == frozenset({"ik:oku", "ik:onay"})


def test_admin_ik_onay_alir() -> None:
    # admin tüm kataloğa sahip → ik:onay dâhil (izin onaylayabilir).
    assert "ik:onay" in VARSAYILAN_ROLLER["admin"]
