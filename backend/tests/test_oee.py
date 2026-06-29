"""OEE saf hesaplama fonksiyonu birim testleri.

OEE = Kullanılabilirlik × Performans × Kalite. Saf fonksiyon (DB/IO yok) → kolay test.
"""

from __future__ import annotations

import pytest

from app.modules.uretim.oee import OeeSonuc, oee_hesapla


def test_bilinen_girdiler() -> None:
    s = oee_hesapla(
        planlanan_sure_dk=480,
        durus_sure_dk=48,
        toplam_adet=500,
        saglam_adet=490,
        ideal_cevrim_sn=50,
    )
    assert isinstance(s, OeeSonuc)
    # Kullanılabilirlik = (480-48)/480 = 0.9
    assert s.kullanilabilirlik == pytest.approx(0.9)
    # Kalite = 490/500 = 0.98
    assert s.kalite == pytest.approx(0.98)
    # Performans = (500*50/60) / 432 = 416.667/432 ≈ 0.96451
    assert s.performans == pytest.approx(0.96451, rel=1e-3)
    assert s.oee == pytest.approx(0.9 * 0.96451 * 0.98, rel=1e-3)


def test_planlanan_sure_sifir_oee_sifir() -> None:
    s = oee_hesapla(
        planlanan_sure_dk=0, durus_sure_dk=0, toplam_adet=0, saglam_adet=0, ideal_cevrim_sn=50
    )
    assert s.kullanilabilirlik == 0.0
    assert s.oee == 0.0


def test_toplam_adet_sifir_kalite_sifir() -> None:
    s = oee_hesapla(
        planlanan_sure_dk=480, durus_sure_dk=0, toplam_adet=0, saglam_adet=0, ideal_cevrim_sn=50
    )
    assert s.kalite == 0.0
    assert s.performans == 0.0
    assert s.oee == 0.0


def test_durus_planlanandan_buyukse_kullanilabilirlik_sifir() -> None:
    s = oee_hesapla(
        planlanan_sure_dk=100, durus_sure_dk=150, toplam_adet=10, saglam_adet=10, ideal_cevrim_sn=60
    )
    assert s.kullanilabilirlik == 0.0
    assert s.oee == 0.0


def test_performans_bir_ile_sinirli() -> None:
    # Üretim ideal hızdan daha hızlıysa performans 1.0'ı geçmez.
    s = oee_hesapla(
        planlanan_sure_dk=100,
        durus_sure_dk=0,
        toplam_adet=1000,
        saglam_adet=1000,
        ideal_cevrim_sn=60,
    )
    assert s.performans == 1.0


def test_mukemmel_uretim_oee_bir() -> None:
    s = oee_hesapla(
        planlanan_sure_dk=480, durus_sure_dk=0, toplam_adet=576, saglam_adet=576, ideal_cevrim_sn=50
    )
    # ideal_time = 576*50/60 = 480 = calisma → performans 1.0; kalite 1.0; kullanilabilirlik 1.0
    assert s.oee == pytest.approx(1.0)


def test_negatif_girdi_hata() -> None:
    with pytest.raises(ValueError):
        oee_hesapla(
            planlanan_sure_dk=-1, durus_sure_dk=0, toplam_adet=0, saglam_adet=0, ideal_cevrim_sn=50
        )


def test_saglam_toplamdan_buyuk_hata() -> None:
    with pytest.raises(ValueError):
        oee_hesapla(
            planlanan_sure_dk=100,
            durus_sure_dk=0,
            toplam_adet=10,
            saglam_adet=20,
            ideal_cevrim_sn=60,
        )
