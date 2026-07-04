"""S12 saf birim testleri — sözleşme/talep durum makineleri + yaklaşan hesap + depolama."""

from __future__ import annotations

from datetime import date

import pytest

from app.modules.crm.birimler import FIRMA_TIPLERI
from app.modules.dys.depolama import BellekNesneDepo, belge_nesne_anahtari
from app.modules.sozlesme import durum as sdurum
from app.modules.sozlesme.hesap import kalan_gun, yaklasiyor_mu
from app.modules.talep import durum as tdurum


# --- Sözleşme durum makinesi ---
def test_sozlesme_ilk_gecisler() -> None:
    assert sdurum.gecis_gecerli_mi("taslak", "aktif")
    assert sdurum.gecis_gecerli_mi("taslak", "iptal")
    assert not sdurum.gecis_gecerli_mi("taslak", "sonlandi")


def test_sozlesme_aktif_gecisleri() -> None:
    assert sdurum.gecerli_hedefler("aktif") == frozenset({"sonlandi", "feshedildi", "iptal"})


def test_sozlesme_terminal_cikissiz() -> None:
    for t in sdurum.TERMINAL_DURUMLAR:
        assert sdurum.gecerli_hedefler(t) == frozenset()


def test_sozlesme_bilinmeyen_durum_bos() -> None:
    assert sdurum.gecerli_hedefler("uzay") == frozenset()


# --- Talep durum makinesi ---
def test_talep_akis() -> None:
    assert tdurum.gecis_gecerli_mi("acik", "inceleniyor")
    assert tdurum.gecis_gecerli_mi("inceleniyor", "cozuldu")
    assert tdurum.gecis_gecerli_mi("cozuldu", "kapandi")
    # yeniden aç
    assert tdurum.gecis_gecerli_mi("cozuldu", "inceleniyor")
    # doğrudan atlamalar yasak
    assert not tdurum.gecis_gecerli_mi("acik", "cozuldu")
    assert not tdurum.gecis_gecerli_mi("kapandi", "acik")


def test_talep_terminal() -> None:
    assert frozenset({"kapandi", "iptal"}) == tdurum.TERMINAL_DURUMLAR


# --- Yaklaşan sözleşme saf hesabı ---
def test_kalan_gun() -> None:
    assert kalan_gun(date(2026, 1, 31), date(2026, 1, 1)) == 30
    assert kalan_gun(date(2025, 12, 20), date(2026, 1, 1)) == -12


@pytest.mark.parametrize(
    ("bitis", "bugun", "esik", "beklenen"),
    [
        (date(2026, 1, 20), date(2026, 1, 1), 30, True),  # 19 gün ≤ 30
        (date(2026, 1, 1), date(2026, 1, 1), 30, True),  # bugün biter → kalan 0
        (date(2026, 3, 1), date(2026, 1, 1), 30, False),  # çok uzak
        (date(2025, 12, 20), date(2026, 1, 1), 30, False),  # süresi geçmiş → yaklaşan değil
    ],
)
def test_yaklasiyor_mu(bitis: date, bugun: date, esik: int, beklenen: bool) -> None:
    assert yaklasiyor_mu(bitis, bugun, esik) is beklenen


# --- Firma tipi beyaz-listesi ---
def test_firma_tipleri() -> None:
    assert frozenset({"musteri", "tedarikci", "her_ikisi"}) == FIRMA_TIPLERI


# --- Nesne depolama anahtarı + bellek deposu ---
def test_belge_nesne_anahtari_tenant_onekli() -> None:
    a = belge_nesne_anahtari("alfa", 7, 2, "rapor.pdf")
    assert a == "tenant_alfa/belge/7/2/rapor.pdf"
    # farklı tenant farklı önek → izolasyon
    assert belge_nesne_anahtari("beta", 7, 2, "rapor.pdf").startswith("tenant_beta/")


def test_bellek_nesne_depo_yukle_indir() -> None:
    depo = BellekNesneDepo()
    depo.yukle("k1", b"merhaba", "text/plain")
    assert depo.var_mi("k1")
    assert depo.indir("k1") == b"merhaba"
    depo.sil("k1")
    assert not depo.var_mi("k1")
    with pytest.raises(KeyError):
        depo.indir("k1")
