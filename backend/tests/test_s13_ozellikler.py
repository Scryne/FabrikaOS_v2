"""S13 feature pipeline testleri (saf pandas; DB yok).

Sentetik üretim/arıza/stok verisiyle ``modules/ai/ozellikler.py`` sözleşmesi doğrulanır:
kolon adları, OEE matematiğinin ``oee_hesapla`` ile tutarlılığı, etiketleme ve pencereler.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from app.modules.ai import ozellikler
from app.modules.uretim.oee import oee_hesapla

_BASLANGIC = datetime(2026, 6, 1, 8, 0, tzinfo=UTC)


def _uretim_cerceve(gun_sayisi: int = 14, makineler: tuple[int, ...] = (1, 2)) -> pd.DataFrame:
    """Makine başına günde iki üretim kaydı üretir (tz-aware zaman)."""
    satirlar = []
    for makine_id in makineler:
        for g in range(gun_sayisi):
            for saat in (0, 6):
                satirlar.append(
                    {
                        "zaman": _BASLANGIC + timedelta(days=g, hours=saat),
                        "makine_id": makine_id,
                        "planlanan_sure_dk": 240.0,
                        "durus_sure_dk": 20.0 + 5 * makine_id,
                        "toplam_adet": 200,
                        "saglam_adet": 190,
                        "ideal_cevrim_sn": 60.0,
                    }
                )
    return pd.DataFrame(satirlar)


def _ariza_cerceve() -> pd.DataFrame:
    # makine 1: 10. günde arıza (0-indeksli 9. gün)
    return pd.DataFrame([{"makine_id": 1, "baslangic": _BASLANGIC + timedelta(days=9, hours=3)}])


# --- gunluk_makine_ozeti ---
def test_gunluk_ozet_gruplar_ve_oee_hesaplar() -> None:
    gunluk = ozellikler.gunluk_makine_ozeti(_uretim_cerceve(gun_sayisi=3, makineler=(1,)))
    assert len(gunluk) == 3  # gün başına tek satır
    ilk = gunluk.iloc[0]
    beklenen = oee_hesapla(
        planlanan_sure_dk=480.0,
        durus_sure_dk=50.0,
        toplam_adet=400,
        saglam_adet=380,
        ideal_cevrim_sn=60.0,
    )
    assert abs(ilk["oee"] - beklenen.oee) < 1e-9
    assert abs(ilk["kullanilabilirlik"] - beklenen.kullanilabilirlik) < 1e-9
    assert abs(ilk["durus_orani"] - 50.0 / 480.0) < 1e-9
    assert abs(ilk["fire_orani"] - 20.0 / 400.0) < 1e-9
    # gun kolonu tz'siz normalize edilir
    assert ilk["gun"] == pd.Timestamp("2026-06-01")


def test_gunluk_ozet_bos_girdi() -> None:
    bos = ozellikler.gunluk_makine_ozeti(pd.DataFrame())
    assert bos.empty
    assert set(ozellikler.GUNLUK_KOLONLAR) <= set(bos.columns)


# --- bakım özellikleri ---
def test_bakim_ozellikleri_etiket_ariza_penceresinde() -> None:
    gunluk = ozellikler.gunluk_makine_ozeti(_uretim_cerceve())
    egitim = ozellikler.bakim_ozellikleri(gunluk, _ariza_cerceve(), pencere=3, ufuk=7)
    assert set(ozellikler.BAKIM_OZELLIKLERI) <= set(egitim.columns)
    assert "ariza_var" in egitim.columns
    m1 = egitim[egitim["makine_id"] == 1].set_index("gun")
    # arıza 2026-06-10'da: (gun, gun+7] penceresine düşen günler etiketlenir
    assert m1.loc[pd.Timestamp("2026-06-05"), "ariza_var"] == 1
    assert m1.loc[pd.Timestamp("2026-06-09"), "ariza_var"] == 1
    assert m1.loc[pd.Timestamp("2026-06-10"), "ariza_var"] == 0  # aynı gün pencere dışı
    assert m1.loc[pd.Timestamp("2026-06-01"), "ariza_var"] == 0
    # makine 2'de hiç arıza yok → tüm etiketler 0, son_arizadan_gun tavanda
    m2 = egitim[egitim["makine_id"] == 2]
    assert (m2["ariza_var"] == 0).all()
    assert (m2["son_arizadan_gun"] == ozellikler.ARIZA_GUN_TAVANI).all()


def test_bakim_ozellikleri_ariza_sonrasi_sayac() -> None:
    gunluk = ozellikler.gunluk_makine_ozeti(_uretim_cerceve())
    egitim = ozellikler.bakim_ozellikleri(gunluk, _ariza_cerceve(), pencere=3, ufuk=7)
    m1 = egitim[egitim["makine_id"] == 1].set_index("gun")
    assert m1.loc[pd.Timestamp("2026-06-11"), "son_arizadan_gun"] == 1.0
    assert m1.loc[pd.Timestamp("2026-06-14"), "son_arizadan_gun"] == 4.0
    assert m1.loc[pd.Timestamp("2026-06-11"), "ariza_sayisi_30g"] == 1
    assert m1.loc[pd.Timestamp("2026-06-09"), "ariza_sayisi_30g"] == 0


def test_bakim_guncel_ozellikler_makine_basina_tek_satir() -> None:
    gunluk = ozellikler.gunluk_makine_ozeti(_uretim_cerceve())
    guncel = ozellikler.bakim_guncel_ozellikler(gunluk, _ariza_cerceve(), pencere=3)
    assert len(guncel) == 2
    assert set(guncel["makine_id"]) == {1, 2}
    # her makinenin son günü
    assert (guncel["gun"] == pd.Timestamp("2026-06-14")).all()
    assert "ariza_var" not in guncel.columns


# --- OEE gecikme özellikleri ---
def test_oee_gecikme_ozellikleri_kaydirma() -> None:
    gunluk = ozellikler.gunluk_makine_ozeti(_uretim_cerceve(gun_sayisi=10, makineler=(1,)))
    lagli = ozellikler.oee_gecikme_ozellikleri(gunluk, gecikme=3)
    # 10 gün − 3 gecikme = 7 satır
    assert len(lagli) == 7
    satir = lagli.iloc[0]
    seri = gunluk.sort_values("gun")["oee"].tolist()
    assert abs(satir["oee_gecikme_1"] - seri[2]) < 1e-9
    assert abs(satir["oee_gecikme_3"] - seri[0]) < 1e-9
    assert abs(satir["oee"] - seri[3]) < 1e-9


def test_oee_son_pencere_en_yeni_ilk() -> None:
    gunluk = ozellikler.gunluk_makine_ozeti(_uretim_cerceve(gun_sayisi=10))
    son = ozellikler.oee_son_pencere(gunluk, gecikme=3)
    assert len(son) == 2
    seri = gunluk[gunluk["makine_id"] == 1].sort_values("gun")["oee"].tolist()
    satir = son[son["makine_id"] == 1].iloc[0]
    assert abs(satir["oee_gecikme_1"] - seri[-1]) < 1e-9  # en yeni gün
    assert abs(satir["oee_gecikme_3"] - seri[-3]) < 1e-9


def test_oee_son_pencere_yetersiz_gecmis_atlanir() -> None:
    gunluk = ozellikler.gunluk_makine_ozeti(_uretim_cerceve(gun_sayisi=2))
    son = ozellikler.oee_son_pencere(gunluk, gecikme=7)
    assert son.empty


# --- stok tüketimi ---
def test_stok_tuketim_gunluk_yalniz_cikis() -> None:
    hareketler = pd.DataFrame(
        [
            {"malzeme_id": 5, "tur": "cikis", "miktar": 10.0, "zaman": _BASLANGIC},
            {
                "malzeme_id": 5,
                "tur": "cikis",
                "miktar": 4.0,
                "zaman": _BASLANGIC + timedelta(hours=2),
            },
            {"malzeme_id": 5, "tur": "giris", "miktar": 99.0, "zaman": _BASLANGIC},
            {
                "malzeme_id": 7,
                "tur": "cikis",
                "miktar": 2.5,
                "zaman": _BASLANGIC + timedelta(days=1),
            },
        ]
    )
    gunluk = ozellikler.stok_tuketim_gunluk(hareketler)
    assert len(gunluk) == 2
    m5 = gunluk[gunluk["malzeme_id"] == 5].iloc[0]
    assert m5["miktar"] == 14.0  # giriş sayılmaz
    assert m5["gun"] == pd.Timestamp("2026-06-01")


def test_stok_tuketim_bos_girdi() -> None:
    bos = ozellikler.stok_tuketim_gunluk(pd.DataFrame())
    assert bos.empty
    assert {"malzeme_id", "gun", "miktar"} <= set(bos.columns)
