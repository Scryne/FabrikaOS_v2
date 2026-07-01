"""S10: izin katalogu + varsayılan roller (kalite/enerji görev rolleri)."""

from __future__ import annotations

from app.kimlik.izinler import IZIN_KATALOGU, VARSAYILAN_ROLLER


def test_enerji_yaz_katalogda() -> None:
    assert "enerji:yaz" in IZIN_KATALOGU


def test_kalite_rolu() -> None:
    assert VARSAYILAN_ROLLER["kalite"] == frozenset({"kalite:oku", "kalite:yaz"})


def test_enerji_rolu() -> None:
    assert VARSAYILAN_ROLLER["enerji"] == frozenset({"enerji:oku", "enerji:yaz"})


def test_izleyici_enerji_okur_yazmaz() -> None:
    # izleyici tüm :oku'ları alır (enerji:oku dahil) ama enerji:yaz almaz.
    assert "enerji:oku" in VARSAYILAN_ROLLER["izleyici"]
    assert "enerji:yaz" not in VARSAYILAN_ROLLER["izleyici"]


def test_admin_yeni_izni_alir() -> None:
    assert "enerji:yaz" in VARSAYILAN_ROLLER["admin"]
