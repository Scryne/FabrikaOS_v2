"""S29 (ADR-0048) saf çekirdek: fatura durum makinesi, KDV/yuvarlama, cari işareti, yaşlandırma."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.modules.finans import durum, hesap

D = Decimal


def test_durum_makinesi_gecisleri() -> None:
    assert durum.gecis_gecerli_mi("taslak", "onay_bekliyor")
    assert durum.gecis_gecerli_mi("onay_bekliyor", "kesildi")
    assert durum.gecis_gecerli_mi("onay_bekliyor", "taslak")  # iade
    assert durum.gecis_gecerli_mi("kesildi", "kapandi")
    assert durum.gecis_gecerli_mi("kesildi", "iptal")
    assert not durum.gecis_gecerli_mi("taslak", "kesildi")  # onaysız kesilmez
    assert not durum.gecis_gecerli_mi("kapandi", "iptal")
    assert not durum.gecis_gecerli_mi("iptal", "taslak")
    assert durum.gecerli_hedefler("bilinmeyen") == frozenset()
    assert {d for d in durum.DURUMLAR if not durum.gecerli_hedefler(d)} == durum.TERMINAL_DURUMLAR


def test_kalem_satir_basina_yuvarlanir() -> None:
    k = hesap.kalem_hesapla(D("3"), D("33.335"), 20)
    assert k.satir_tutari == D("100.01")  # 100.005 → yarım yukarı
    assert k.kdv_tutari == D("20.00")  # 100.01 × %20 = 20.002
    sifir = hesap.kalem_hesapla(D("1"), D("0"), 0)
    assert (sifir.satir_tutari, sifir.kdv_tutari) == (D("0.00"), D("0.00"))
    bir = hesap.kalem_hesapla(D("1"), D("0.05"), 10)
    assert bir.kdv_tutari == D("0.01")  # 0.005 → 0.01 (yarım yukarı, aşağı değil)
    # Yasal oranların hepsi kabul edilir (%0, %1, %10, %20); başkası reddedilir.
    assert [hesap.kalem_hesapla(D("100"), D("1"), o).kdv_tutari for o in (0, 1, 10, 20)] == [
        D("0.00"),
        D("1.00"),
        D("10.00"),
        D("20.00"),
    ]
    with pytest.raises(ValueError):
        hesap.kalem_hesapla(D("1"), D("1"), 2)


def test_toplam_yuvarlanmis_satirlarin_toplami() -> None:
    kalemler = [hesap.kalem_hesapla(D("1"), D("0.125"), 20) for _ in range(3)]
    t = hesap.fatura_toplami(kalemler)
    # her satır 0.13 (0.125 yukarı) + KDV 0.03 (0.026) → toplam satırlar üstünden
    assert (t.ara_toplam, t.kdv_toplam, t.genel_toplam) == (D("0.39"), D("0.09"), D("0.48"))
    bos = hesap.fatura_toplami([])
    assert bos.genel_toplam == D("0.00")


@pytest.mark.parametrize(
    ("miktar", "fiyat", "oran"),
    [(D("0"), D("1"), 20), (D("-1"), D("1"), 20), (D("1"), D("-0.01"), 20), (D("1"), D("1"), 18)],
)
def test_gecersiz_kalem_reddedilir(miktar: Decimal, fiyat: Decimal, oran: int) -> None:
    with pytest.raises(ValueError):
        hesap.kalem_hesapla(miktar, fiyat, oran)


def test_cari_isareti() -> None:
    assert hesap.fatura_cari_etkisi("satis", D("100")) == D("100")
    assert hesap.fatura_cari_etkisi("alis", D("100")) == D("-100")
    assert hesap.odeme_cari_etkisi("tahsilat", D("40")) == D("-40")
    assert hesap.odeme_cari_etkisi("odeme", D("40")) == D("40")
    # satış 100 + tahsilat 100 = 0; alış 100 + ödeme 100 = 0
    assert hesap.fatura_cari_etkisi("satis", D("100")) + hesap.odeme_cari_etkisi(
        "tahsilat", D("100")
    ) == D("0")
    assert hesap.fatura_cari_etkisi("alis", D("100")) + hesap.odeme_cari_etkisi(
        "odeme", D("100")
    ) == D("0")
    with pytest.raises(ValueError):
        hesap.fatura_cari_etkisi("iade", D("1"))
    with pytest.raises(ValueError):
        hesap.odeme_cari_etkisi("virman", D("1"))


def test_odeme_fatura_uyumu_ve_acik_tutar() -> None:
    assert hesap.odeme_faturaya_uyar_mi("tahsilat", "satis")
    assert hesap.odeme_faturaya_uyar_mi("odeme", "alis")
    assert not hesap.odeme_faturaya_uyar_mi("tahsilat", "alis")
    assert not hesap.odeme_faturaya_uyar_mi("odeme", "satis")
    assert hesap.acik_tutar(D("100"), D("30")) == D("70")
    assert hesap.acik_tutar(D("100"), D("100")) == D("0")
    assert hesap.acik_tutar(D("100"), D("120")) == D("0.00")


@pytest.mark.parametrize(
    ("vade", "kova"),
    [
        (date(2026, 11, 2), "vadesi_gelmemis"),
        (date(2026, 11, 1), "0_30"),
        (date(2026, 10, 2), "0_30"),
        (date(2026, 10, 1), "31_60"),
        (date(2026, 9, 2), "31_60"),
        (date(2026, 9, 1), "61_90"),
        (date(2026, 8, 3), "61_90"),
        (date(2026, 8, 2), "90_ustu"),
    ],
)
def test_yaslandirma_sinirlari(vade: date, kova: str) -> None:
    assert hesap.yaslandirma_kovasi(vade, date(2026, 11, 1)) == kova
