"""S28 (ADR-0047): mutasyon testinin bulduğu boşlukları kapatan sınır testleri.

``scripts/mutasyon.py`` ilk koşuda %57,7 verdi: SPC kurallarının sınırları (tam 3σ, tam 2σ),
Shewhart sabit tablosunun çoğu, OEE'nin sıfır korumaları ve hakediş/eğitim matrisinin yıl ve ay
sınırları hiç sınanmıyordu. Buradaki her test bir mutant sınıfını öldürmek için yazıldı.
"""

from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from app.modules.ik.izin_hakedis import izin_bakiyesi, tam_yil, yillik_hak
from app.modules.isg.egitim_matrisi import Katilim, ay_ekle, hucre
from app.modules.kalite import spc
from app.modules.uretim.oee import oee_hesapla

# ── SPC: sabitler ───────────────────────────────────────────────────────────

# ASTM E2587-16 Tablo / Montgomery Ek VI (n: A2, D3, D4, d2).
ASTM = {
    2: (1.880, 0.000, 3.267, 1.128),
    3: (1.023, 0.000, 2.574, 1.693),
    4: (0.729, 0.000, 2.282, 2.059),
    5: (0.577, 0.000, 2.114, 2.326),
    6: (0.483, 0.000, 2.004, 2.534),
    7: (0.419, 0.076, 1.924, 2.704),
    8: (0.373, 0.136, 1.864, 2.847),
    9: (0.337, 0.184, 1.816, 2.970),
    10: (0.308, 0.223, 1.777, 3.078),
}


def test_shewhart_sabitleri_astm_tablosuyla_birebir() -> None:
    assert spc.SABITLER == ASTM


@pytest.mark.parametrize("n", sorted(ASTM))
def test_sabitler_kendi_icinde_tutarli(n: int) -> None:
    a2, d3, d4, d2 = spc.SABITLER[n]
    assert a2 * d2 * math.sqrt(n) == pytest.approx(3, rel=0.01)  # A2 = 3 / (d2·√n)
    assert d3 + d4 == pytest.approx(2, abs=0.002) or d3 == 0


# ── SPC: limitler ve yetenek ────────────────────────────────────────────────


def test_limitler_elle_hesapla() -> None:
    lim = spc.xbar_r_limitleri([[1, 2, 3], [2, 3, 4]])  # n=3, X̿=2,5, R̄=2
    assert (lim.n, lim.alt_grup_sayisi) == (3, 2)
    assert lim.xbar_cl == pytest.approx(2.5)
    assert lim.xbar_ucl == pytest.approx(2.5 + 1.023 * 2)
    assert lim.xbar_lcl == pytest.approx(2.5 - 1.023 * 2)
    assert (lim.r_cl, lim.r_ucl, lim.r_lcl) == pytest.approx((2, 2.574 * 2, 0))
    assert lim.sigma_xbar == pytest.approx(1.023 * 2 / 3)


def test_yetenek_formulleri() -> None:
    lim = spc.xbar_r_limitleri([[9.9, 10.0, 10.1], [9.95, 10.05, 10.0]])
    y = spc.yetenek(lim, alt_tolerans=9.5, ust_tolerans=10.7)
    assert y is not None
    sigma = lim.r_cl / 1.693
    assert y.sigma_ic == pytest.approx(sigma)
    assert y.cp == pytest.approx(1.2 / (6 * sigma))
    assert y.cpk == pytest.approx(min(10.7 - lim.xbar_cl, lim.xbar_cl - 9.5) / (3 * sigma))
    tek = spc.yetenek(lim, alt_tolerans=None, ust_tolerans=10.7)
    assert tek is not None and tek.cp is None
    assert tek.cpk == pytest.approx((10.7 - lim.xbar_cl) / (3 * sigma))
    assert spc.yetenek(lim, alt_tolerans=None, ust_tolerans=None) is None
    sifir = spc.xbar_r_limitleri([[5, 5], [5, 5]])
    assert spc.yetenek(sifir, alt_tolerans=4, ust_tolerans=6) is None  # σ = 0


# ── SPC: Western Electric sınırları (cl=0, σ=1) ─────────────────────────────


def _kurallar(noktalar: list[float]) -> set[tuple[int, int]]:
    return {(i.kural, i.indeks) for i in spc.western_electric(noktalar, 0.0, 1.0)}


def test_kural1_tam_sinir_ihlal_degil() -> None:
    assert _kurallar([3.0]) == set()
    assert _kurallar([3.01]) == {(1, 0)}
    assert _kurallar([-3.01]) == {(1, 0)}


def test_kural2_sinir_ve_tamamlayan_nokta() -> None:
    assert (2, 2) in _kurallar([0, 2.5, 2.5])
    assert (2, 2) in _kurallar([0, -2.5, -2.5])
    assert not any(k == 2 for k, _ in _kurallar([0, 2.0, 2.5]))  # tam 2σ sayılmaz
    assert not any(k == 2 for k, _ in _kurallar([0, 2.5, 1.9]))  # tamamlayan nokta bölgede değil
    assert not any(k == 2 for k, _ in _kurallar([2.5, 2.5]))  # pencere 3 noktadan az


def test_kural3_sinir() -> None:
    assert (3, 4) in _kurallar([0, 1.5, 1.5, 1.5, 1.5])
    assert (3, 4) in _kurallar([0, -1.5, -1.5, -1.5, -1.5])
    assert not any(k == 3 for k, _ in _kurallar([0, 1.0, 1.5, 1.5, 1.5]))  # tam 1σ sayılmaz
    assert not any(k == 3 for k, _ in _kurallar([1.5, 1.5, 1.5, 1.5]))


def test_kural4_sekiz_nokta_ve_merkez() -> None:
    assert (4, 7) in _kurallar([0.5] * 8)
    assert (4, 7) in _kurallar([-0.5] * 8)
    assert not any(k == 4 for k, _ in _kurallar([0.5] * 7))
    assert not any(
        k == 4 for k, _ in _kurallar([0.5] * 7 + [0.0])
    )  # merkezdeki nokta zinciri keser
    assert not any(k == 4 for k, _ in _kurallar([0.5] * 7 + [-0.5]))


def test_sigma_sifirsa_kural_yok() -> None:
    assert spc.western_electric([5.0, 9.0], 0.0, 0.0) == []


def test_r_karti_sinirlari() -> None:
    lim = spc.Limitler(5, 20, 10, 11, 9, r_cl=1.0, r_ucl=2.0, r_lcl=0.5)
    ihlaller = spc.r_karti_ihlalleri([2.0, 2.01, 0.5, 0.49, 1.0], lim)
    assert [i.indeks for i in ihlaller] == [1, 3]


# ── OEE sıfır korumaları ────────────────────────────────────────────────────


def test_oee_sifir_sinirlari() -> None:
    s = oee_hesapla(
        planlanan_sure_dk=1, durus_sure_dk=0, toplam_adet=1, saglam_adet=1, ideal_cevrim_sn=60
    )
    assert (s.kullanilabilirlik, s.performans, s.kalite, s.oee) == (1.0, 1.0, 1.0, 1.0)
    s = oee_hesapla(
        planlanan_sure_dk=10, durus_sure_dk=10, toplam_adet=0, saglam_adet=0, ideal_cevrim_sn=0
    )
    assert (s.kullanilabilirlik, s.performans, s.kalite) == (0.0, 0.0, 0.0)
    s = oee_hesapla(
        planlanan_sure_dk=10, durus_sure_dk=5, toplam_adet=2, saglam_adet=1, ideal_cevrim_sn=60
    )
    assert (s.kullanilabilirlik, s.performans, s.kalite) == pytest.approx((0.5, 0.4, 0.5))
    with pytest.raises(ValueError):
        oee_hesapla(
            planlanan_sure_dk=10,
            durus_sure_dk=-0.1,
            toplam_adet=1,
            saglam_adet=1,
            ideal_cevrim_sn=1,
        )


# ── Hakediş ve eğitim matrisi sınırları ─────────────────────────────────────


def test_tam_yil_azaltma_ve_artik_gun_yildonumu() -> None:
    assert tam_yil(date(2020, 3, 15), date(2022, 3, 14)) == 1
    assert tam_yil(date(2021, 1, 1), date(2020, 6, 1)) == 0
    b = izin_bakiyesi(ise_giris=date(2020, 2, 29), dogum=None, bugun=date(2023, 3, 1), kullanilan=0)
    assert [s.dogdugu_tarih for s in b.satirlar] == [
        date(2021, 2, 28),
        date(2022, 2, 28),
        date(2023, 2, 28),
    ]


def test_bakiye_tarihsiz_ve_sonraki_kademe() -> None:
    b = izin_bakiyesi(ise_giris=None, dogum=None, bugun=date(2026, 1, 1), kullanilan=4)
    assert (b.hakedilen, b.kullanilan, b.bakiye, b.kidem_yili) == (0, 4, -4, 0)
    assert (b.sonraki_hak_tarihi, b.sonraki_hak_gun, b.satirlar) == (None, 0, ())
    # 5 tam yıl: sonraki (6.) yıl 20 güne çıkar.
    b = izin_bakiyesi(
        ise_giris=date(2020, 6, 1), dogum=date(1990, 1, 1), bugun=date(2025, 7, 1), kullanilan=0
    )
    assert (b.kidem_yili, b.sonraki_hak_gun, b.sonraki_hak_tarihi) == (5, 20, date(2026, 6, 1))
    assert yillik_hak(1, None) == 14


def test_egitim_esik_ve_ay_sonu() -> None:
    assert ay_ekle(date(2026, 1, 31), 3) == date(2026, 4, 30)
    bugun = date(2026, 11, 1)

    def durum(tarih: date, ay: int) -> str:
        return hucre([Katilim(1, "k", tarih, ay)], zorunlu=True, bugun=bugun).durum

    # 12 ay geçerli → bitiş = tarih + 12 ay.
    assert durum(bugun + timedelta(days=30) - timedelta(days=365), 12) == "yaklasiyor"
    assert durum(date(2025, 12, 1), 12) == "yaklasiyor"  # bitiş tam 30 gün sonra
    assert durum(date(2025, 12, 2), 12) == "gecerli"  # 31 gün sonra
    assert durum(date(2025, 11, 1), 12) == "yaklasiyor"  # bitiş bugün: henüz geçmedi
    assert durum(date(2025, 10, 31), 12) == "gecmis"
    assert durum(date(2025, 10, 2), 1) == "gecmis"  # 1 ay: süresiz değil


# ── İkinci tur: pencere sınırları ve ölçek (mutasyon 2. koşusunun kalanları) ──


def test_kurallar_pencere_disini_saymaz_ve_gelecege_bakmaz() -> None:
    k = _kurallar
    # Kural 2: yalnız son 3 nokta; ne öncesi ne sonrası sayılır.
    assert (2, 3) not in k([2.5, 0, 0, 2.5])
    assert (2, 2) not in k([0, 0, 2.5, 2.5])
    # Kural 3: yalnız son 5 nokta.
    assert (3, 5) not in k([1.5, 0, 0, 1.5, 1.5, 1.5])
    assert (3, 4) not in k([0, 1.5, 1.5, 0, 1.5, 1.5])
    # Kural 4: tam 8 nokta; öncesindeki karşı taraf noktası zinciri bozar, sonrası etkilemez.
    assert (4, 7) not in k([-0.5] + [0.5] * 7)
    assert (4, 7) in k([0.5] * 8 + [-0.5])
    assert (4, 7) not in k([-0.5] * 7 + [0.0])  # merkez noktası "aşağı" sayılmaz


def test_kurallar_olcekten_bagimsiz() -> None:
    # cl=10, σ=2: 3σ=6, 2σ=4, 1σ=2 — sonuç cl=0/σ=1'deki karşılığıyla aynı olmalı.
    def k(noktalar: list[float]) -> set[tuple[int, int]]:
        return {(i.kural, i.indeks) for i in spc.western_electric(noktalar, 10.0, 2.0)}

    assert k([16.0]) == set() and k([16.02]) == {(1, 0)} and k([3.98]) == {(1, 0)}
    assert (2, 2) in k([10, 15, 15]) and (2, 2) not in k([10, 14, 15])
    assert (2, 2) in k([10, 5, 5])
    assert (3, 4) in k([10, 13, 13, 13, 13]) and (3, 4) not in k([10, 12, 13, 13, 13])
    assert (3, 4) in k([10, 7, 7, 7, 7])


def test_r_karti_kural_numarasi() -> None:
    lim = spc.Limitler(5, 20, 10, 11, 9, r_cl=1.0, r_ucl=2.0, r_lcl=0.5)
    assert {(i.kart, i.kural) for i in spc.r_karti_ihlalleri([3.0], lim)} == {("r", 1)}


def test_sonraki_hak_kademe_gecisi() -> None:
    dort = izin_bakiyesi(
        ise_giris=date(2020, 6, 1), dogum=date(1990, 1, 1), bugun=date(2024, 7, 1), kullanilan=0
    )
    assert (dort.kidem_yili, dort.sonraki_hak_gun) == (4, 14)  # 5. yıl hâlâ 14
