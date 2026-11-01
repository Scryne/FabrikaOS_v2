"""S32 (ADR-0051) saf emisyon hesabı: faktör seçimi, birim, kapsam, faktörsüz tüketim, yoğunluk."""

from __future__ import annotations

from datetime import date
from decimal import Decimal as D

from app.modules.esg.hesap import (
    Faktor,
    Tuketim,
    birim_normalle,
    faktor_sec,
    hesapla,
    yogunluk,
)

ELK_ESKI = Faktor("elektrik", "kwh", D("0.5"), "kapsam2", date(2020, 1, 1), "eski")
ELK_YENI = Faktor("elektrik", "kwh", D("0.4"), "kapsam2", date(2026, 1, 1), "yeni")
GAZ = Faktor("dogalgaz", "m3", D("2"), "kapsam1", date(2020, 1, 1), "gaz")
FAKTORLER = [ELK_YENI, GAZ, ELK_ESKI]


def test_birim_normalle() -> None:
    assert birim_normalle("kWh", D(5)) == ("kwh", D(5))
    assert birim_normalle(" MWh ", D(2)) == ("kwh", D(2000))
    assert birim_normalle("m³", D(3)) == ("m3", D(3))
    assert birim_normalle("Sm3", D(3)) == ("m3", D(3))
    assert birim_normalle("Litre", D(7)) == ("litre", D(7))


def test_faktor_sec_tarih_tur_ve_birim() -> None:
    assert faktor_sec(FAKTORLER, "elektrik", "kwh", date(2025, 12, 31)) is ELK_ESKI
    assert faktor_sec(FAKTORLER, "elektrik", "kwh", date(2026, 1, 1)) is ELK_YENI
    assert faktor_sec(FAKTORLER, "elektrik", "kwh", date(2019, 12, 31)) is None
    assert faktor_sec(FAKTORLER, "elektrik", "m3", date(2026, 5, 1)) is None
    assert faktor_sec(FAKTORLER, "su", "m3", date(2026, 5, 1)) is None


def test_hesap_bilinen_seri() -> None:
    tuketim = [
        Tuketim(date(2025, 12, 1), "elektrik", "kWh", D(1000)),  # eski faktör: 500 kg
        Tuketim(date(2026, 1, 1), "elektrik", "kWh", D(1000)),  # yeni faktör: 400 kg
        Tuketim(date(2026, 1, 1), "elektrik", "MWh", D(1)),  # 1000 kWh → 400 kg
        Tuketim(date(2026, 1, 1), "dogalgaz", "m3", D(50)),  # 100 kg, kapsam 1
        Tuketim(date(2026, 1, 1), "hava", "m3", D(300)),  # faktörsüz
    ]
    s = hesapla(tuketim, FAKTORLER)
    aralik, ocak = s.donemler
    assert (aralik.donem, aralik.kapsam1, aralik.kapsam2) == (date(2025, 12, 1), D(0), D(500))
    assert (ocak.kapsam1, ocak.kapsam2, ocak.toplam) == (D(100), D(800), D(900))
    assert ocak.elektrik_kwh == D(2000) and aralik.elektrik_kwh == D(1000)
    assert (s.kapsam1, s.kapsam2, s.toplam) == (D(100), D(1300), D(1400))
    turler = {(t.enerji_turu, t.birim): t for t in s.turler}
    assert turler[("elektrik", "kwh")].miktar == D(3000)
    assert turler[("elektrik", "kwh")].emisyon == D(1300)
    assert turler[("dogalgaz", "m3")].faktor is GAZ
    # Faktörsüz tüketim 0 sayılmaz, ayrıca listelenir.
    assert [(f.enerji_turu, f.birim, f.miktar) for f in s.faktorsuz] == [("hava", "m3", D(300))]


def test_birimi_uyusmayan_tuketim_faktorsuzdur() -> None:
    s = hesapla([Tuketim(date(2026, 2, 1), "dogalgaz", "kWh", D(10))], FAKTORLER)
    assert s.toplam == 0
    assert [(f.enerji_turu, f.birim) for f in s.faktorsuz] == [("dogalgaz", "kwh")]


def test_bos_girdi_ve_siralama() -> None:
    bos = hesapla([], FAKTORLER)
    assert bos.donemler == [] and bos.toplam == 0
    s = hesapla(
        [
            Tuketim(date(2026, 3, 1), "dogalgaz", "m3", D(1)),
            Tuketim(date(2026, 2, 1), "elektrik", "kwh", D(1)),
        ],
        FAKTORLER,
    )
    assert [d.donem for d in s.donemler] == [date(2026, 2, 1), date(2026, 3, 1)]
    assert [t.enerji_turu for t in s.turler] == ["dogalgaz", "elektrik"]


def test_yogunluk() -> None:
    assert yogunluk(D(900), 300) == D(3)
    assert yogunluk(D(900), 0) is None
    assert yogunluk(D(0), 10) == D(0)


def test_elektrik_kwh_yalniz_elektrigi_sayar_ve_nm3() -> None:
    s = hesapla(
        [
            Tuketim(date(2026, 4, 1), "dogalgaz", "kWh", D(10)),  # kWh ama elektrik değil
            Tuketim(date(2026, 4, 1), "elektrik", "m3", D(10)),  # elektrik ama kWh değil
            Tuketim(date(2026, 4, 1), "dogalgaz", "Nm3", D(4)),  # Nm3 → m3 × 1
        ],
        FAKTORLER,
    )
    assert s.donemler[0].elektrik_kwh == 0
    assert s.donemler[0].kapsam1 == D(8)  # 4 m3 × 2


def test_tek_adette_yogunluk_tanimli() -> None:
    assert yogunluk(D(7), 1) == D(7)
