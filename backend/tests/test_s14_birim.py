"""S14 birim testleri: rapor modülü saf sabitleri (tür/biçim/durum + dosya adı)."""

from __future__ import annotations

from app.modules.rapor import birimler


def test_rapor_turleri() -> None:
    assert frozenset({"uretim", "stok", "kalite", "enerji", "isemri"}) == birimler.RAPOR_TURLERI


def test_rapor_bicimleri() -> None:
    assert frozenset({"pdf", "xlsx"}) == birimler.RAPOR_BICIMLERI


def test_rapor_durumlari() -> None:
    assert frozenset({"kuyrukta", "hazirlaniyor", "hazir", "basarisiz"}) == birimler.RAPOR_DURUMLARI


def test_icerik_tipleri_bicimlerle_ayni_anahtarlar() -> None:
    assert set(birimler.ICERIK_TIPLERI) == set(birimler.RAPOR_BICIMLERI)
    assert birimler.ICERIK_TIPLERI["pdf"] == "application/pdf"
    assert "spreadsheetml" in birimler.ICERIK_TIPLERI["xlsx"]


def test_rapor_dosya_adi() -> None:
    assert birimler.rapor_dosya_adi("RP-2026-000001", "pdf") == "RP-2026-000001.pdf"
    assert birimler.rapor_dosya_adi("RP-2026-000042", "xlsx") == "RP-2026-000042.xlsx"
