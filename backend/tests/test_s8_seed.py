"""S8 seed: saha izinleri + saha-cihaz rolü provizyon tohumunda yer alır."""

from __future__ import annotations

from app.kimlik.izinler import IZIN_KATALOGU, VARSAYILAN_ROLLER


def test_saha_izinleri_katalogda() -> None:
    assert "saha:oku" in IZIN_KATALOGU
    assert "saha:yaz" in IZIN_KATALOGU
    assert "edge" in IZIN_KATALOGU


def test_admin_tum_saha_izinlerine_sahip() -> None:
    assert {"saha:oku", "saha:yaz", "edge"} <= VARSAYILAN_ROLLER["admin"]


def test_izleyici_yalniz_okur() -> None:
    assert "saha:oku" in VARSAYILAN_ROLLER["izleyici"]
    assert "edge" not in VARSAYILAN_ROLLER["izleyici"]


def test_saha_cihaz_rolu_edge_tasir() -> None:
    assert VARSAYILAN_ROLLER["saha-cihaz"] == frozenset({"edge"})
