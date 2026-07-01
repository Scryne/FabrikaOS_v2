"""S10 birim testleri: CAPA durum makinesi + kalite/enerji sabitleri (saf, DB'siz)."""

from __future__ import annotations

from app.modules.enerji import birimler as enerji_birimler
from app.modules.kalite import birimler as kalite_birimler
from app.modules.kalite import durum


def test_ilk_durum_acik() -> None:
    assert durum.ILK_DURUM == "acik"


def test_acik_gecerli_hedefler() -> None:
    assert durum.gecerli_hedefler("acik") == frozenset({"kok_neden", "iptal"})


def test_dogrulama_hedefleri_geri_donus_dahil() -> None:
    # doğrulama başarısız → uygulama'ya geri; başarılı → kapandi; veya iptal
    assert durum.gecerli_hedefler("dogrulama") == frozenset({"kapandi", "uygulama", "iptal"})


def test_terminal_durumlardan_cikis_yok() -> None:
    for d in ("kapandi", "iptal"):
        assert durum.gecerli_hedefler(d) == frozenset()
    assert frozenset({"kapandi", "iptal"}) == durum.TERMINAL_DURUMLAR


def test_aktif_durumlar() -> None:
    assert (
        frozenset({"acik", "kok_neden", "aksiyon_plani", "uygulama", "dogrulama"})
        == durum.AKTIF_DURUMLAR
    )


def test_gecerli_ve_gecersiz_gecisler() -> None:
    assert durum.gecis_gecerli_mi("acik", "kok_neden") is True
    assert durum.gecis_gecerli_mi("dogrulama", "kapandi") is True
    assert durum.gecis_gecerli_mi("dogrulama", "uygulama") is True
    # acik'ten doğrudan kapandi yasak
    assert durum.gecis_gecerli_mi("acik", "kapandi") is False
    # terminalden çıkış yasak
    assert durum.gecis_gecerli_mi("kapandi", "uygulama") is False
    # tanımsız durum → boş
    assert durum.gecis_gecerli_mi("yok", "acik") is False


def test_kalite_sabitler() -> None:
    assert frozenset({"gecti", "kaldi", "sartli"}) == kalite_birimler.KONTROL_SONUCLARI
    assert frozenset({"uretim", "giris", "final"}) == kalite_birimler.KONTROL_TURLERI
    assert frozenset({"dusuk", "orta", "yuksek", "kritik"}) == kalite_birimler.UYGUNSUZLUK_ONEMLERI
    assert frozenset({"duzeltici", "onleyici"}) == kalite_birimler.CAPA_AKSIYON_TURLERI
    assert frozenset({"planlandi", "tamamlandi", "iptal"}) == kalite_birimler.CAPA_AKSIYON_DURUMLARI


def test_enerji_sabitler() -> None:
    assert (
        frozenset({"elektrik", "dogalgaz", "su", "hava", "buhar"}) == enerji_birimler.ENERJI_TURLERI
    )
