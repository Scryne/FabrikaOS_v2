"""S9 birim testleri: satınalma talebi durum makinesi + stok sabitleri (saf, DB'siz)."""

from __future__ import annotations

from app.modules.stok import birimler, talep_durum


def test_ilk_durum_taslak() -> None:
    assert talep_durum.ILK_DURUM == "taslak"


def test_taslak_gecerli_hedefler() -> None:
    assert talep_durum.gecerli_hedefler("taslak") == frozenset({"onay_bekliyor", "iptal"})


def test_onay_bekliyor_gecerli_hedefler() -> None:
    assert talep_durum.gecerli_hedefler("onay_bekliyor") == frozenset(
        {"onaylandi", "reddedildi", "iptal"}
    )


def test_terminal_durumlardan_cikis_yok() -> None:
    for d in ("onaylandi", "reddedildi", "iptal"):
        assert talep_durum.gecerli_hedefler(d) == frozenset()
    assert frozenset({"onaylandi", "reddedildi", "iptal"}) == talep_durum.TERMINAL_DURUMLAR


def test_gecerli_ve_gecersiz_gecisler() -> None:
    assert talep_durum.gecis_gecerli_mi("taslak", "onay_bekliyor") is True
    assert talep_durum.gecis_gecerli_mi("onay_bekliyor", "onaylandi") is True
    # taslak'tan doğrudan onaylandı yasak (önce gönderilmeli)
    assert talep_durum.gecis_gecerli_mi("taslak", "onaylandi") is False
    # terminalden çıkış yasak
    assert talep_durum.gecis_gecerli_mi("onaylandi", "iptal") is False
    # tanımsız durum → boş
    assert talep_durum.gecis_gecerli_mi("yok", "taslak") is False


def test_sabitler() -> None:
    assert {"adet", "kg", "litre", "metre"} <= birimler.BIRIMLER
    assert frozenset({"giris", "cikis", "duzeltme"}) == birimler.STOK_HAREKET_TURLERI
