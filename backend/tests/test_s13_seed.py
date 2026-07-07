"""S13 seed: AI izin kataloğu (ai:oku + ai:egit) + ai rolü."""

from __future__ import annotations

from app.kimlik.izinler import IZIN_KATALOGU, VARSAYILAN_ROLLER


def test_s13_izinleri_katalogda() -> None:
    for kod in ("ai:oku", "ai:egit"):
        assert kod in IZIN_KATALOGU


def test_ai_rolu() -> None:
    assert VARSAYILAN_ROLLER["ai"] == frozenset({"ai:oku", "ai:egit"})


def test_izleyici_ai_okur_ama_egitemez() -> None:
    izleyici = VARSAYILAN_ROLLER["izleyici"]
    assert "ai:oku" in izleyici
    assert "ai:egit" not in izleyici


def test_admin_ai_egit_alir() -> None:
    assert "ai:egit" in VARSAYILAN_ROLLER["admin"]
