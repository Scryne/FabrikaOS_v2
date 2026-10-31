"""S26-B saf kurallar (ADR-0044): yıllık izin hakedişi ve İSG eğitim matrisi."""

from __future__ import annotations

from datetime import date

from app.modules.ik.izin_hakedis import izin_bakiyesi, tam_yil, yillik_hak
from app.modules.isg.egitim_matrisi import Katilim, ay_ekle, hucre, matris


def test_tam_yil_yildonumu_ve_artik_gun() -> None:
    assert tam_yil(date(2020, 3, 15), date(2021, 3, 14)) == 0
    assert tam_yil(date(2020, 3, 15), date(2021, 3, 15)) == 1
    assert tam_yil(date(2020, 2, 29), date(2021, 2, 28)) == 1  # artık gün yıldönümü 28 Şubat
    assert tam_yil(date(2020, 1, 1), date(2019, 1, 1)) == 0


def test_kanuni_kademeler_ve_yas_alt_siniri() -> None:
    assert [yillik_hak(y, 30) for y in (0, 1, 5, 6, 14, 15, 20)] == [0, 14, 14, 20, 20, 26, 26]
    assert yillik_hak(2, 18) == 20  # 18 yaş ve altı en az 20
    assert yillik_hak(2, 50) == 20  # 50 yaş ve üstü en az 20
    assert yillik_hak(2, 19) == 14
    assert yillik_hak(16, 55) == 26  # alt sınır kademe hakkını düşürmez
    assert yillik_hak(2, 30, sozlesme_hakki=18) == 18  # sözleşme daha cömertse o geçerli
    assert yillik_hak(7, 30, sozlesme_hakki=18) == 20  # kanun daha cömertse kanun


def test_bakiye_kumulatif_devreder() -> None:
    # 2018-06-01 giriş, 2026-11-01: 8 tam yıl → 5×14 + 3×20 = 130
    b = izin_bakiyesi(
        ise_giris=date(2018, 6, 1), dogum=date(1990, 1, 1), bugun=date(2026, 11, 1), kullanilan=100
    )
    assert b.kidem_yili == 8
    assert b.hakedilen == 5 * 14 + 3 * 20
    assert b.bakiye == 30
    assert b.sonraki_hak_tarihi == date(2027, 6, 1)
    assert b.sonraki_hak_gun == 20
    assert [s.gun for s in b.satirlar][-1] == 20


def test_ilk_yil_dolmadan_hak_yok_ve_yasa_gore_satir() -> None:
    b = izin_bakiyesi(ise_giris=date(2026, 3, 1), dogum=None, bugun=date(2026, 11, 1), kullanilan=0)
    assert (b.hakedilen, b.bakiye, b.kidem_yili) == (0, 0, 0)
    # 49 yaşında başlayan: 1. yıl sonunda 50 → 20 gün
    b = izin_bakiyesi(
        ise_giris=date(2024, 5, 1), dogum=date(1975, 3, 1), bugun=date(2026, 11, 1), kullanilan=0
    )
    assert [s.gun for s in b.satirlar] == [20, 20]
    assert (
        izin_bakiyesi(ise_giris=None, dogum=None, bugun=date(2026, 1, 1), kullanilan=3).bakiye == -3
    )


def test_ay_ekle_ay_sonu() -> None:
    assert ay_ekle(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert ay_ekle(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert ay_ekle(date(2026, 11, 15), 14) == date(2028, 1, 15)


def test_hucre_durumlari() -> None:
    bugun = date(2026, 11, 1)

    def k(tarih: date, ay: int = 12) -> Katilim:
        return Katilim(1, "yangin", tarih, ay)

    assert hucre([], zorunlu=True, bugun=bugun).durum == "eksik"
    assert hucre([], zorunlu=False, bugun=bugun).durum == "gerekmez"
    assert hucre([k(date(2026, 3, 1))], zorunlu=True, bugun=bugun).durum == "gecerli"
    h = hucre([k(date(2025, 11, 20))], zorunlu=True, bugun=bugun)
    assert (h.durum, h.gecerlilik_sonu) == ("yaklasiyor", date(2026, 11, 20))
    assert hucre([k(date(2025, 10, 1))], zorunlu=True, bugun=bugun).durum == "gecmis"
    # en yeni katılım belirler; eski geçmiş kayıt hücreyi kırmızıya çekmez
    assert hucre([k(date(2023, 1, 1)), k(date(2026, 6, 1))], zorunlu=True, bugun=bugun).durum == (
        "gecerli"
    )
    assert hucre([k(date(2010, 1, 1), 0)], zorunlu=True, bugun=bugun).durum == "gecerli"  # süresiz


def test_matris_departman_ve_genel_gereksinim() -> None:
    bugun = date(2026, 11, 1)
    sutunlar, m = matris(
        [(1, "uretim"), (2, "idari")],
        [
            Katilim(1, "temel_isg", date(2026, 1, 10), 12),
            Katilim(2, "ilk_yardim", date(2026, 2, 1), 36),
        ],
        {"": frozenset({"temel_isg"}), "uretim": frozenset({"yuksekte_calisma"})},
        bugun=bugun,
    )
    assert sutunlar == ["ilk_yardim", "temel_isg", "yuksekte_calisma"]
    assert m[1]["temel_isg"].durum == "gecerli"
    assert m[1]["yuksekte_calisma"].durum == "eksik"
    assert m[1]["ilk_yardim"].durum == "gerekmez"
    assert m[2]["temel_isg"].durum == "eksik"  # genel gereksinim herkese
    assert m[2]["yuksekte_calisma"].durum == "gerekmez"  # yalnız üretime zorunlu
    assert m[2]["ilk_yardim"].durum == "gecerli"
