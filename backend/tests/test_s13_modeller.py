"""S13 model katmanı testleri (saf scikit-learn; DB yok).

Sentetik veriyle **çıktı doğrulama**: alan sözleşmeleri, değer aralıkları, sıralama,
determinizm (sabit random_state) ve az-veri (``YetersizVeri``) yolları.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from app.modules.ai import birimler, modeller, ozellikler


# --- yardımcı sentetik çerçeveler ---
def _bakim_egitim_cerceve(satir: int = 60) -> pd.DataFrame:
    """Yüksek duruşlu makine-günler arızayla etiketli; düşük duruşlular sağlıklı."""
    satirlar = []
    for i in range(satir):
        riskli = i % 2 == 0
        satirlar.append(
            {
                "makine_id": 1 if riskli else 2,
                "gun": pd.Timestamp("2026-05-01") + pd.Timedelta(days=i),
                "oee_ort": 0.45 if riskli else 0.85,
                "durus_orani_ort": 0.40 if riskli else 0.04,
                "fire_orani_ort": 0.12 if riskli else 0.01,
                "ariza_sayisi_30g": 3 if riskli else 0,
                "son_arizadan_gun": 2.0 if riskli else 90.0,
                "ariza_var": 1 if riskli else 0,
            }
        )
    return pd.DataFrame(satirlar)


def _bakim_guncel_cerceve() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "makine_id": 1,
                "gun": pd.Timestamp("2026-06-30"),
                "oee_ort": 0.45,
                "durus_orani_ort": 0.40,
                "fire_orani_ort": 0.12,
                "ariza_sayisi_30g": 3,
                "son_arizadan_gun": 2.0,
            },
            {
                "makine_id": 2,
                "gun": pd.Timestamp("2026-06-30"),
                "oee_ort": 0.85,
                "durus_orani_ort": 0.04,
                "fire_orani_ort": 0.01,
                "ariza_sayisi_30g": 0,
                "son_arizadan_gun": 90.0,
            },
        ]
    )


def _gunluk_cerceve(aykiri: bool = True) -> pd.DataFrame:
    """Normal makine-günler + (istenirse) bariz bir aykırı gözlem."""
    satirlar = [
        {
            "makine_id": 1 + (i % 3),
            "gun": pd.Timestamp("2026-05-01") + pd.Timedelta(days=i // 3),
            "kullanilabilirlik": 0.9,
            "performans": 0.85 + 0.01 * (i % 5),
            "kalite": 0.97,
            "oee": 0.75,
            "durus_orani": 0.05 + 0.005 * (i % 4),
            "fire_orani": 0.02,
            "toplam_adet": 400,
        }
        for i in range(60)
    ]
    if aykiri:
        satirlar.append(
            {
                "makine_id": 9,
                "gun": pd.Timestamp("2026-06-21"),
                "kullanilabilirlik": 0.2,
                "performans": 0.15,
                "kalite": 0.5,
                "oee": 0.015,
                "durus_orani": 0.85,
                "fire_orani": 0.45,
                "toplam_adet": 40,
            }
        )
    return pd.DataFrame(satirlar)


def _oee_lagli_cerceve(gecikme: int = 3) -> pd.DataFrame:
    """Sabit ~0.8 OEE serisinden lag çerçevesi (iki makine)."""
    gunluk = pd.DataFrame(
        [
            {
                "makine_id": m,
                "gun": pd.Timestamp("2026-05-01") + pd.Timedelta(days=g),
                "oee": 0.8 + 0.01 * ((g + m) % 3),
            }
            for m in (1, 2)
            for g in range(30)
        ]
    )
    return ozellikler.oee_gecikme_ozellikleri(gunluk, gecikme=gecikme)


def _tuketim_cerceve() -> pd.DataFrame:
    """Malzeme 5: günde 10 birim, 10 gün. Malzeme 7: günde 2 birim."""
    return pd.DataFrame(
        [
            {
                "malzeme_id": mid,
                "gun": pd.Timestamp("2026-06-01") + pd.Timedelta(days=g),
                "miktar": hiz,
            }
            for mid, hiz in ((5, 10.0), (7, 2.0))
            for g in range(10)
        ]
    )


def _malzeme_cerceve() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "malzeme_id": 5,
                "kod": "MLZ-5",
                "ad": "Cıvata",
                "birim": "adet",
                "mevcut_miktar": 50.0,
                "kritik_stok": 20.0,
            },
            {
                "malzeme_id": 7,
                "kod": "MLZ-7",
                "ad": "Yağ",
                "birim": "litre",
                "mevcut_miktar": 100.0,
                "kritik_stok": 10.0,
            },
        ]
    )


# --- kestirimci bakım ---
def test_bakim_egit_ve_tahmin_riskli_makine_yuksek() -> None:
    sonuc = modeller.kestirimci_bakim_egit(_bakim_egitim_cerceve())
    assert sonuc.metrikler["satir_sayisi"] == 60
    assert 0.0 <= sonuc.metrikler["dogruluk"] <= 1.0
    tahminler = modeller.kestirimci_bakim_tahmin(sonuc.nesne, _bakim_guncel_cerceve())
    assert len(tahminler) == 2
    # riskli makine 1 listenin başında ve skoru sağlıklı makine 2'den yüksek
    assert tahminler[0]["makine_id"] == 1
    assert tahminler[0]["risk_skoru"] > tahminler[1]["risk_skoru"]
    for t in tahminler:
        assert 0.0 <= t["risk_skoru"] <= 1.0
        assert t["seviye"] in birimler.RISK_SEVIYELERI
    json.dumps(tahminler)  # JSON-serileştirilebilir


def test_bakim_egit_deterministik() -> None:
    a = modeller.kestirimci_bakim_egit(_bakim_egitim_cerceve())
    b = modeller.kestirimci_bakim_egit(_bakim_egitim_cerceve())
    ta = modeller.kestirimci_bakim_tahmin(a.nesne, _bakim_guncel_cerceve())
    tb = modeller.kestirimci_bakim_tahmin(b.nesne, _bakim_guncel_cerceve())
    assert ta == tb


def test_bakim_yetersiz_veri() -> None:
    with pytest.raises(modeller.YetersizVeri):
        modeller.kestirimci_bakim_egit(_bakim_egitim_cerceve(satir=5))


def test_bakim_tek_sinif_sifir_risk() -> None:
    df = _bakim_egitim_cerceve()
    df["ariza_var"] = 0  # hiç arıza görmemiş tenant
    sonuc = modeller.kestirimci_bakim_egit(df)
    tahminler = modeller.kestirimci_bakim_tahmin(sonuc.nesne, _bakim_guncel_cerceve())
    assert all(t["risk_skoru"] == 0.0 for t in tahminler)


# --- anomali ---
def test_anomali_aykiri_gozlem_tespit_edilir() -> None:
    sonuc = modeller.anomali_egit(_gunluk_cerceve())
    bulgular = modeller.anomali_tahmin(sonuc.nesne, _gunluk_cerceve())
    assert len(bulgular) >= 1
    # en aykırı (en düşük skor) ilk sırada = enjekte edilen gözlem
    assert bulgular[0]["makine_id"] == 9
    assert bulgular[0]["gun"] == "2026-06-21"
    for b in bulgular:
        assert set(ozellikler.ANOMALI_OZELLIKLERI) <= set(b)
    json.dumps(bulgular)


def test_anomali_yetersiz_veri() -> None:
    with pytest.raises(modeller.YetersizVeri):
        modeller.anomali_egit(_gunluk_cerceve().head(5))


# --- OEE tahmini ---
def test_oee_egit_ve_ufuk_tahmini() -> None:
    lagli = _oee_lagli_cerceve(gecikme=3)
    sonuc = modeller.oee_egit(lagli, gecikme=3)
    assert sonuc.metrikler["satir_sayisi"] == len(lagli)
    son = pd.DataFrame(
        [
            {
                "makine_id": 1,
                "son_gun": pd.Timestamp("2026-05-30"),
                "oee_gecikme_1": 0.8,
                "oee_gecikme_2": 0.81,
                "oee_gecikme_3": 0.8,
            },
        ]
    )
    tahminler = modeller.oee_tahmin(sonuc.nesne, son, ufuk=5)
    assert len(tahminler) == 1
    m = tahminler[0]
    assert m["makine_id"] == 1
    assert len(m["tahminler"]) == 5
    assert m["tahminler"][0]["gun"] == "2026-05-31"
    for nokta in m["tahminler"]:
        assert 0.0 <= nokta["oee"] <= 1.0
        assert abs(nokta["oee"] - 0.8) < 0.1  # durağan seri → durağan tahmin
    json.dumps(tahminler)


def test_oee_yetersiz_veri() -> None:
    with pytest.raises(modeller.YetersizVeri):
        modeller.oee_egit(_oee_lagli_cerceve(gecikme=3).head(5), gecikme=3)


# --- stok ihtiyaç ---
def test_stok_egit_ve_kalan_gun() -> None:
    sonuc = modeller.stok_egit(_tuketim_cerceve())
    assert sonuc.metrikler["malzeme_sayisi"] == 2
    tahminler = modeller.stok_tahmin(sonuc.nesne, _malzeme_cerceve())
    assert len(tahminler) == 2
    m5 = next(t for t in tahminler if t["malzeme_id"] == 5)
    assert abs(m5["gunluk_tuketim"] - 10.0) < 1.5
    assert abs(m5["kalan_gun"] - 5.0) < 1.0  # 50 mevcut / ~10 günlük
    assert abs(m5["onerilen_siparis"] - 250.0) < 40.0  # 30g ihtiyaç − mevcut
    # en kritik (kalan_gun en az) ilk sırada
    assert tahminler[0]["malzeme_id"] == 5
    json.dumps(tahminler)


def test_stok_yetersiz_veri() -> None:
    with pytest.raises(modeller.YetersizVeri):
        modeller.stok_egit(pd.DataFrame(columns=["malzeme_id", "gun", "miktar"]))


def test_stok_tuketimsiz_malzeme_atlanir() -> None:
    sonuc = modeller.stok_egit(_tuketim_cerceve())
    malzemeler = pd.concat(
        [
            _malzeme_cerceve(),
            pd.DataFrame(
                [
                    {
                        "malzeme_id": 99,
                        "kod": "MLZ-99",
                        "ad": "Atıl",
                        "birim": "adet",
                        "mevcut_miktar": 10.0,
                        "kritik_stok": 1.0,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    tahminler = modeller.stok_tahmin(sonuc.nesne, malzemeler)
    assert {t["malzeme_id"] for t in tahminler} == {5, 7}
