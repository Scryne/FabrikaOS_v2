"""S26 SPC saf çekirdeği: X̄-R limitleri, Western Electric kuralları, Cp/Cpk (ADR-0025)."""

from __future__ import annotations

import pytest

from app.modules.kalite.spc import (
    SpcHatasi,
    r_karti_ihlalleri,
    western_electric,
    xbar_r_limitleri,
    yetenek,
)


def _kurallar(noktalar: list[float]) -> list[tuple[int, int]]:
    return [(i.kural, i.indeks) for i in western_electric(noktalar, cl=0.0, sigma=1.0)]


def test_limitler_bilinen_seri() -> None:
    # Her alt grubun ortalaması 10, aralığı 2 → X̿ = 10, R̄ = 2; n = 5 için A2 = 0,577, D4 = 2,114.
    alt_gruplar = [[9.0, 10.0, 11.0, 10.0, 10.0]] * 4
    lim = xbar_r_limitleri(alt_gruplar)
    assert lim.n == 5
    assert lim.xbar_cl == pytest.approx(10.0)
    assert lim.xbar_ucl == pytest.approx(11.154)
    assert lim.xbar_lcl == pytest.approx(8.846)
    assert lim.r_cl == pytest.approx(2.0)
    assert lim.r_ucl == pytest.approx(4.228)
    assert lim.r_lcl == 0.0
    # n = 7'de D3 > 0: R kartının alt limiti sıfır değildir.
    assert xbar_r_limitleri([[0, 1, 2, 3, 4, 5, 6]] * 3).r_lcl == pytest.approx(0.076 * 6)


@pytest.mark.parametrize(
    ("alt_gruplar", "mesaj"),
    [
        ([[1.0, 2.0]], "en az"),
        ([[1.0, 2.0], [1.0, 2.0, 3.0]], "aynı boyutta"),
        ([[1.0]] * 3, "2 ile 10"),
    ],
)
def test_limit_girdisi_dogrulanir(alt_gruplar: list[list[float]], mesaj: str) -> None:
    with pytest.raises(SpcHatasi, match=mesaj):
        xbar_r_limitleri(alt_gruplar)


def test_kural_1_limit_disi() -> None:
    assert _kurallar([0.0, 0.5, 3.5, -3.2]) == [(1, 2), (1, 3)]
    assert _kurallar([2.9, -2.9]) == []


def test_kural_2_ucte_iki_2_sigma() -> None:
    assert (2, 2) in _kurallar([0.1, 2.5, 2.2])
    assert (2, 2) in _kurallar([-2.5, 0.0, -2.1])
    assert _kurallar([2.5, -2.5, 0.1]) == []  # iki nokta ama karşı taraflarda
    assert _kurallar([2.5, 0.1, 1.9]) == []  # tamamlayan nokta 2σ'nın ötesinde değil


def test_kural_3_beste_dort_1_sigma() -> None:
    assert (3, 4) in _kurallar([1.5, 1.2, 0.2, 1.3, 1.1])
    assert all(k != 3 for k, _ in _kurallar([1.5, 1.2, 0.2, 0.3, 1.1]))


def test_kural_4_sekiz_ayni_taraf() -> None:
    assert _kurallar([0.1] * 8) == [(4, 7)]
    assert _kurallar([0.1] * 7 + [-0.1]) == []
    assert _kurallar([0.1] * 9) == [(4, 7), (4, 8)]  # desen sürdükçe her yeni nokta işaretlenir


def test_kararli_seri_ihlalsiz_ve_kayma_yakalanir() -> None:
    tohum = [0.3, -0.5, 0.8, -0.2, 0.1, -0.7, 0.4, -0.1, 0.6, -0.4, 0.2, -0.3]
    assert western_electric(tohum, cl=0.0, sigma=1.0) == []
    kaymis = [*tohum, 1.4, 1.6, 1.2, 1.8]
    assert {k for k, _ in _kurallar(kaymis)} == {3}


def test_r_karti_ve_yetenek() -> None:
    lim = xbar_r_limitleri([[9.0, 10.0, 11.0, 10.0, 10.0]] * 4)
    assert [(i.kart, i.indeks) for i in r_karti_ihlalleri([2.0, 5.0, 1.0], lim)] == [("r", 1)]
    y = yetenek(lim, alt_tolerans=7, ust_tolerans=13)
    assert y is not None
    assert y.sigma_ic == pytest.approx(2.0 / 2.326)
    assert y.cp == pytest.approx(6 / (6 * (2.0 / 2.326)))
    assert y.cpk == pytest.approx(y.cp)
    tek = yetenek(lim, alt_tolerans=None, ust_tolerans=11)
    assert tek is not None
    assert tek.cp is None
    assert tek.cpk == pytest.approx(1 / (3 * (2.0 / 2.326)))
    assert yetenek(lim, alt_tolerans=None, ust_tolerans=None) is None
