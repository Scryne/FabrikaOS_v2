"""S13 birim testleri: AI modülü saf sabitleri + risk seviyesi eşlemesi."""

from __future__ import annotations

import pytest

from app.modules.ai import birimler


def test_model_turleri() -> None:
    assert frozenset({"kestirimci_bakim", "anomali", "oee", "stok"}) == birimler.MODEL_TURLERI


def test_model_durumlari() -> None:
    assert frozenset({"egitiliyor", "hazir", "basarisiz"}) == birimler.MODEL_DURUMLARI


def test_risk_seviyesi_esikler() -> None:
    assert birimler.risk_seviyesi(0.0) == "dusuk"
    assert birimler.risk_seviyesi(0.32) == "dusuk"
    assert birimler.risk_seviyesi(0.33) == "orta"
    assert birimler.risk_seviyesi(0.65) == "orta"
    assert birimler.risk_seviyesi(0.66) == "yuksek"
    assert birimler.risk_seviyesi(1.0) == "yuksek"


def test_risk_seviyesi_aralik_disi_hata() -> None:
    for skor in (-0.1, 1.1):
        with pytest.raises(ValueError):
            birimler.risk_seviyesi(skor)


def test_risk_seviyeleri_kumesi() -> None:
    assert frozenset({"dusuk", "orta", "yuksek"}) == birimler.RISK_SEVIYELERI
