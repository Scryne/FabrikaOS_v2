"""S31 (ADR-0050) saf MRP ve sipariş durum makinesi."""

from __future__ import annotations

from decimal import Decimal as D

import pytest

from app.modules.satis import durum
from app.modules.satis.mrp import Kalem, MalzemeIhtiyaci, brut_ihtiyac, hesapla

# Ürün 1: 2 × malzeme 10 + 0,5 × malzeme 11. Ürün 2: 3 × malzeme 10. Ürün 3: reçetesiz.
RECETE = {1: [(10, D(2)), (11, D("0.5"))], 2: [(10, D(3))]}


def test_brut_patlatma_ayni_malzemeyi_toplar_receteziz_urunu_ayirir() -> None:
    brut, recetesiz = brut_ihtiyac([Kalem(1, D(10)), Kalem(2, D(4)), Kalem(3, D(1))], RECETE)
    assert brut == {10: D(32), 11: D(5)}  # 10×2 + 4×3 = 32; 10×0,5 = 5
    assert recetesiz == [3]
    brut2, recetesiz2 = brut_ihtiyac([Kalem(3, D(1)), Kalem(3, D(2)), Kalem(4, D(1))], {})
    assert brut2 == {} and recetesiz2 == [3, 4]  # tekil ve sıralı


def test_net_ihtiyac_acik_tedarik_ve_ayrilmisla() -> None:
    s = hesapla(
        [Kalem(1, D(10))],
        RECETE,
        eldeki={10: D(15), 11: D(100)},
        acik_tedarik={10: D(3)},
        ayrilmis={10: D(4), 11: D(98)},
    )
    m10, m11 = s.ihtiyaclar
    assert (m10.malzeme_id, m10.brut, m10.kullanilabilir, m10.net) == (10, D(20), D(14), D(6))
    assert (m11.malzeme_id, m11.brut, m11.kullanilabilir, m11.net) == (11, D(5), D(2), D(3))
    assert [e.malzeme_id for e in s.eksikler] == [10, 11]


def test_yeterli_stokta_eksik_yok_ve_net_negatif_olmaz() -> None:
    s = hesapla([Kalem(1, D(1))], RECETE, {10: D(100), 11: D(100)}, {}, {})
    assert all(i.net == 0 for i in s.ihtiyaclar) and s.eksikler == []
    # Tam karşılanan ihtiyaç (brüt == kullanılabilir) eksik sayılmaz.
    tam = hesapla([Kalem(2, D(1))], RECETE, {10: D(3)}, {}, {})
    assert tam.ihtiyaclar[0].net == 0 and tam.eksikler == []


def test_bilinmeyen_malzeme_sifir_stok_ve_siralama() -> None:
    s = hesapla([Kalem(2, D(2)), Kalem(1, D(1))], RECETE, {}, {}, {})
    assert [i.malzeme_id for i in s.ihtiyaclar] == [10, 11]
    assert s.ihtiyaclar[0].eldeki == 0 and s.ihtiyaclar[0].net == D(8)


def test_ayrilmis_stogu_eksiye_dusurebilir() -> None:
    # Açık iş emirleri eldekinden fazlasını bekliyorsa kullanılabilir negatif: net > brüt.
    i = MalzemeIhtiyaci(10, brut=D(5), eldeki=D(2), acik_tedarik=D(0), ayrilmis=D(4))
    assert i.kullanilabilir == D(-2) and i.net == D(7)


@pytest.mark.parametrize(
    "mevcut, hedef, gecerli",
    [
        ("taslak", "onaylandi", True),
        ("taslak", "iptal", True),
        ("taslak", "sevk_edildi", False),
        ("onaylandi", "sevk_edildi", True),
        ("onaylandi", "iptal", True),
        ("onaylandi", "taslak", False),
        ("sevk_edildi", "kapandi", True),
        ("sevk_edildi", "iptal", False),
        ("kapandi", "iptal", False),
        ("iptal", "taslak", False),
        ("yok", "taslak", False),
    ],
)
def test_durum_gecisleri(mevcut: str, hedef: str, gecerli: bool) -> None:
    assert durum.gecis_gecerli_mi(mevcut, hedef) is gecerli


def test_durum_sabitleri() -> None:
    assert durum.ILK_DURUM == "taslak"
    assert {"kapandi", "iptal"} == durum.TERMINAL_DURUMLAR
    assert all(not durum.gecerli_hedefler(t) for t in durum.TERMINAL_DURUMLAR)
    assert {"taslak"} == durum.DUZENLENEBILIR
    assert {"taslak", "onaylandi", "sevk_edildi", "kapandi", "iptal"} == durum.DURUMLAR


def test_kesirli_kucuk_eksik_de_eksiktir() -> None:
    # 1 ürün × 0,5 = 0,5 malzeme 11; stok 0,2 → net 0,3 (birimden küçük ama eksik).
    s = hesapla([Kalem(1, D(1))], RECETE, {10: D(10), 11: D("0.2")}, {}, {})
    assert [(e.malzeme_id, e.net) for e in s.eksikler] == [(11, D("0.3"))]
