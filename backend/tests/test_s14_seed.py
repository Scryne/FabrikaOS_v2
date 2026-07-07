"""S14 seed: analitik/rapor izinleri katalogda + analist rolü (görev ayrımı)."""

from __future__ import annotations

from app.kimlik.izinler import IZIN_KATALOGU, VARSAYILAN_ROLLER


def test_s14_izinleri_katalogda() -> None:
    for kod in ("analitik:oku", "rapor:oku", "rapor:yaz"):
        assert kod in IZIN_KATALOGU


def test_analist_rolu() -> None:
    assert VARSAYILAN_ROLLER["analist"] == frozenset({"analitik:oku", "rapor:oku", "rapor:yaz"})


def test_izleyici_rapor_okur_ama_olusturamaz() -> None:
    izleyici = VARSAYILAN_ROLLER["izleyici"]
    assert "analitik:oku" in izleyici
    assert "rapor:oku" in izleyici
    assert "rapor:yaz" not in izleyici


def test_admin_rapor_yaz_alir() -> None:
    assert "rapor:yaz" in VARSAYILAN_ROLLER["admin"]
