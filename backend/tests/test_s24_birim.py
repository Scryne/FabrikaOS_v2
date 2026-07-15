"""S24 saf birim testleri — duruş pareto + MTBF/MTTR (bilinen serilerle)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.modules.bakim.metrik import mtbf_mttr_hesapla
from app.modules.durus.pareto import pareto_hesapla


# --- Pareto ---
def test_pareto_siralama_yuzde_ve_kumulatif() -> None:
    satirlar = pareto_hesapla(
        [("Ayar", "planli", 100.0), ("Arıza", "plansiz", 300.0), ("Temizlik", "planli", 100.0)]
    )
    assert [s.neden for s in satirlar] == ["Arıza", "Ayar", "Temizlik"]  # dk desc, ad asc
    assert satirlar[0].yuzde == 60.0
    assert satirlar[0].kumulatif_yuzde == 60.0
    assert satirlar[1].kumulatif_yuzde == 80.0
    assert satirlar[2].kumulatif_yuzde == 100.0
    assert satirlar[0].sinif == "plansiz"


def test_pareto_bos_ve_sifir_toplam() -> None:
    assert pareto_hesapla([]) == []
    assert pareto_hesapla([("X", "planli", 0.0)]) == []  # bölme hatası imkânsız


# --- MTBF / MTTR ---
def test_mtbf_mttr_bilinen_seri() -> None:
    bas = datetime(2026, 7, 1, tzinfo=UTC)
    bit = bas + timedelta(days=10)  # pencere 240 saat
    arizalar = [
        (bas + timedelta(days=1), bas + timedelta(days=1, hours=4)),  # 4 saat onarım
        (bas + timedelta(days=5), bas + timedelta(days=5, hours=2)),  # 2 saat onarım
    ]
    sonuc = mtbf_mttr_hesapla(arizalar, pencere_baslangic=bas, pencere_bitis=bit)
    assert sonuc.ariza_sayisi == 2
    assert sonuc.kapanan_ariza == 2
    assert sonuc.toplam_ariza_saat == pytest.approx(6.0)
    assert sonuc.mtbf_saat == pytest.approx((240 - 6) / 2, abs=0.01)
    assert sonuc.mttr_saat == pytest.approx(3.0, abs=0.01)


def test_mtbf_acik_ariza_pencere_sonuna_sayilir_mttr_disi() -> None:
    bas = datetime(2026, 7, 1, tzinfo=UTC)
    bit = bas + timedelta(hours=100)
    arizalar = [(bas + timedelta(hours=90), None)]  # açık arıza: 10 saat pencere içinde
    sonuc = mtbf_mttr_hesapla(arizalar, pencere_baslangic=bas, pencere_bitis=bit)
    assert sonuc.ariza_sayisi == 1
    assert sonuc.kapanan_ariza == 0
    assert sonuc.toplam_ariza_saat == pytest.approx(10.0)
    assert sonuc.mtbf_saat == pytest.approx(90.0)
    assert sonuc.mttr_saat is None  # onarım süresi bilinmiyor


def test_mtbf_ariza_yoksa_none() -> None:
    bas = datetime(2026, 7, 1, tzinfo=UTC)
    sonuc = mtbf_mttr_hesapla([], pencere_baslangic=bas, pencere_bitis=bas + timedelta(days=1))
    assert sonuc.mtbf_saat is None and sonuc.mttr_saat is None
    assert sonuc.ariza_sayisi == 0
