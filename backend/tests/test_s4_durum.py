"""S4 birim testleri: iş emri durum makinesi (saf fonksiyon, DB'siz).

Geçerli yaşam döngüsü: acik → atandi → devam_ediyor → kapandi.
İptal her aktif aşamadan erişilebilir. Terminal durumlardan (kapandi/iptal) çıkış yok.
"""

from __future__ import annotations

import pytest

from app.modules.isemri.durum import (
    ILK_DURUM,
    TERMINAL_DURUMLAR,
    gecerli_hedefler,
    gecis_gecerli_mi,
)


def test_ilk_durum_acik() -> None:
    assert ILK_DURUM == "acik"


def test_terminal_durumlar() -> None:
    assert frozenset({"kapandi", "iptal"}) == TERMINAL_DURUMLAR


@pytest.mark.parametrize(
    ("mevcut", "hedef"),
    [
        ("acik", "atandi"),
        ("atandi", "devam_ediyor"),
        ("devam_ediyor", "kapandi"),
    ],
)
def test_ileri_gecisler_gecerli(mevcut: str, hedef: str) -> None:
    assert gecis_gecerli_mi(mevcut, hedef) is True


@pytest.mark.parametrize("mevcut", ["acik", "atandi", "devam_ediyor"])
def test_iptal_her_aktif_asamadan_gecerli(mevcut: str) -> None:
    assert gecis_gecerli_mi(mevcut, "iptal") is True


@pytest.mark.parametrize(
    ("mevcut", "hedef"),
    [
        ("acik", "kapandi"),  # atlamalı geçiş yasak
        ("acik", "devam_ediyor"),  # atlamalı
        ("atandi", "kapandi"),  # atlamalı
        ("acik", "acik"),  # kendine geçiş yok
        ("devam_ediyor", "atandi"),  # geri geçiş yok
    ],
)
def test_gecersiz_gecisler(mevcut: str, hedef: str) -> None:
    assert gecis_gecerli_mi(mevcut, hedef) is False


@pytest.mark.parametrize("terminal", ["kapandi", "iptal"])
def test_terminal_durumdan_cikis_yok(terminal: str) -> None:
    assert gecerli_hedefler(terminal) == frozenset()
    # Hiçbir hedefe gidilemez (örn. yeniden açma yok).
    assert gecis_gecerli_mi(terminal, "devam_ediyor") is False


def test_gecerli_hedefler_acik() -> None:
    assert gecerli_hedefler("acik") == frozenset({"atandi", "iptal"})


def test_bilinmeyen_durum_hedefsiz() -> None:
    # Tanımsız bir durum güvenli biçimde boş hedef kümesi döndürür (patlamaz).
    assert gecerli_hedefler("ucan-daire") == frozenset()
    assert gecis_gecerli_mi("ucan-daire", "kapandi") is False
