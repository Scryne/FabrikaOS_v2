"""S11 birim testleri: İSG risk matrisi/sabitler + İK izin durum makinesi/sabitler (saf)."""

from __future__ import annotations

import pytest

from app.modules.ik import birimler as ik_birimler
from app.modules.ik import izin_durum
from app.modules.isg import birimler as isg_birimler
from app.modules.isg import risk_matrisi


# --- İSG sabitleri ---
def test_isg_sabitler() -> None:
    assert frozenset({"kaza", "ramak_kala", "meslek_hastaligi"}) == isg_birimler.KAZA_TURLERI
    assert frozenset({"hafif", "orta", "agir", "olumcul"}) == isg_birimler.KAZA_AGIRLIKLARI
    assert frozenset({"acik", "devam", "kapandi"}) == isg_birimler.RISK_DURUMLARI


# --- İSG risk matrisi (saf) ---
def test_risk_skoru_carpim() -> None:
    assert risk_matrisi.risk_skoru(3, 4) == 12
    assert risk_matrisi.risk_skoru(1, 1) == 1
    assert risk_matrisi.risk_skoru(5, 5) == 25


def test_risk_skoru_aralik_disi_hata() -> None:
    for olasilik, siddet in ((0, 3), (6, 2), (2, 0), (3, 6)):
        with pytest.raises(ValueError):
            risk_matrisi.risk_skoru(olasilik, siddet)


def test_risk_seviyesi_esikler() -> None:
    assert risk_matrisi.risk_seviyesi(1) == "dusuk"
    assert risk_matrisi.risk_seviyesi(4) == "dusuk"
    assert risk_matrisi.risk_seviyesi(5) == "orta"
    assert risk_matrisi.risk_seviyesi(9) == "orta"
    assert risk_matrisi.risk_seviyesi(10) == "yuksek"
    assert risk_matrisi.risk_seviyesi(15) == "yuksek"
    assert risk_matrisi.risk_seviyesi(16) == "cok_yuksek"
    assert risk_matrisi.risk_seviyesi(25) == "cok_yuksek"


def test_risk_seviyesi_kume() -> None:
    assert frozenset({"dusuk", "orta", "yuksek", "cok_yuksek"}) == risk_matrisi.RISK_SEVIYELERI
    # her geçerli skor bir seviyeye eşlenir
    for olasilik in range(1, 6):
        for siddet in range(1, 6):
            seviye = risk_matrisi.risk_seviyesi(risk_matrisi.risk_skoru(olasilik, siddet))
            assert seviye in risk_matrisi.RISK_SEVIYELERI


# --- İK sabitleri ---
def test_ik_sabitler() -> None:
    assert (
        frozenset({"yillik", "mazeret", "hastalik", "ucretsiz", "dogum", "babalik"})
        == ik_birimler.IZIN_TURLERI
    )
    assert frozenset({"zimmetli", "iade_edildi"}) == ik_birimler.ZIMMET_DURUMLARI


# --- İK izin talebi durum makinesi (satinalma aynası) ---
def test_izin_ilk_durum_taslak() -> None:
    assert izin_durum.ILK_DURUM == "taslak"


def test_izin_gecerli_hedefler() -> None:
    assert izin_durum.gecerli_hedefler("taslak") == frozenset({"onay_bekliyor", "iptal"})
    assert izin_durum.gecerli_hedefler("onay_bekliyor") == frozenset(
        {"onaylandi", "reddedildi", "iptal"}
    )


def test_izin_terminal_durumlardan_cikis_yok() -> None:
    for d in ("onaylandi", "reddedildi", "iptal"):
        assert izin_durum.gecerli_hedefler(d) == frozenset()
    assert frozenset({"onaylandi", "reddedildi", "iptal"}) == izin_durum.TERMINAL_DURUMLAR


def test_izin_gecerli_ve_gecersiz_gecisler() -> None:
    assert izin_durum.gecis_gecerli_mi("taslak", "onay_bekliyor") is True
    assert izin_durum.gecis_gecerli_mi("onay_bekliyor", "onaylandi") is True
    assert izin_durum.gecis_gecerli_mi("taslak", "onaylandi") is False
    assert izin_durum.gecis_gecerli_mi("onaylandi", "iptal") is False
    assert izin_durum.gecis_gecerli_mi("yok", "taslak") is False
