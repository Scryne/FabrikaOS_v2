"""AI feature pipeline (saf pandas) — ham tenant satırlarından model girdileri.

Girdi sözleşmeleri (repository katmanı bu kolon adlarıyla DataFrame üretir):

- **üretim**: ``zaman, makine_id, planlanan_sure_dk, durus_sure_dk, toplam_adet,
  saglam_adet, ideal_cevrim_sn`` (``uretim_verileri`` satırları).
- **arıza**: ``makine_id, baslangic`` (``ariza_kayitlari`` satırları).
- **stok hareketi**: ``malzeme_id, tur, miktar, zaman`` (``stok_hareketleri`` satırları).

Tüm fonksiyonlar saftır (DB/IO yok); OEE matematiği ``uretim.oee.oee_hesapla`` ile
birebir aynıdır. ``gun`` kolonu tz'siz normalize edilmiş gündür (UTC'ye çevrilip atılır).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from app.modules.uretim.oee import oee_hesapla

# Günlük makine özeti kolon sözleşmesi.
GUNLUK_KOLONLAR = [
    "makine_id",
    "gun",
    "kullanilabilirlik",
    "performans",
    "kalite",
    "oee",
    "durus_orani",
    "fire_orani",
    "toplam_adet",
]

# Kestirimci bakım modelinin özellik kolonları (eğitim + çıkarım aynı sözleşme).
BAKIM_OZELLIKLERI = [
    "oee_ort",
    "durus_orani_ort",
    "fire_orani_ort",
    "ariza_sayisi_30g",
    "son_arizadan_gun",
]

# Anomali modelinin özellik kolonları (günlük özetten seçilir).
ANOMALI_OZELLIKLERI = ["durus_orani", "fire_orani", "performans"]

# Hiç arızası olmayan makine için "son arızadan geçen gün" tavanı.
ARIZA_GUN_TAVANI = 90.0


def _gun_kolonu(seri: pd.Series) -> pd.Series:
    """Zaman kolonunu tz'siz normalize günlere indirger (tz-aware ise UTC üzerinden)."""
    s = pd.to_datetime(seri)
    if s.dt.tz is not None:
        s = s.dt.tz_convert("UTC").dt.tz_localize(None)
    return s.dt.normalize()


def gunluk_makine_ozeti(uretim: pd.DataFrame) -> pd.DataFrame:
    """Üretim satırlarını (makine, gün) düzeyine toplar ve OEE bileşenlerini hesaplar."""
    if uretim.empty:
        return pd.DataFrame(columns=GUNLUK_KOLONLAR)
    df = uretim.copy()
    df["gun"] = _gun_kolonu(df["zaman"])
    grup = df.groupby(["makine_id", "gun"], as_index=False).agg(
        planlanan_sure_dk=("planlanan_sure_dk", "sum"),
        durus_sure_dk=("durus_sure_dk", "sum"),
        toplam_adet=("toplam_adet", "sum"),
        saglam_adet=("saglam_adet", "sum"),
        ideal_cevrim_sn=("ideal_cevrim_sn", "mean"),
    )
    sonuclar = [
        oee_hesapla(
            planlanan_sure_dk=float(s.planlanan_sure_dk),
            durus_sure_dk=float(s.durus_sure_dk),
            toplam_adet=int(s.toplam_adet),
            saglam_adet=int(s.saglam_adet),
            ideal_cevrim_sn=float(s.ideal_cevrim_sn),
        )
        for s in grup.itertuples()
    ]
    grup["kullanilabilirlik"] = [r.kullanilabilirlik for r in sonuclar]
    grup["performans"] = [r.performans for r in sonuclar]
    grup["kalite"] = [r.kalite for r in sonuclar]
    grup["oee"] = [r.oee for r in sonuclar]
    planlanan = grup["planlanan_sure_dk"].astype(float)
    toplam = grup["toplam_adet"].astype(float)
    grup["durus_orani"] = np.where(
        planlanan > 0, grup["durus_sure_dk"].astype(float) / planlanan, 0.0
    )
    grup["fire_orani"] = np.where(
        toplam > 0, (toplam - grup["saglam_adet"].astype(float)) / toplam, 0.0
    )
    return grup[GUNLUK_KOLONLAR].sort_values(["makine_id", "gun"]).reset_index(drop=True)


def _ariza_gunleri(ariza: pd.DataFrame) -> dict[int, np.ndarray]:
    """Makine başına sıralı arıza günleri (normalize, tz'siz)."""
    if ariza.empty:
        return {}
    df = ariza.copy()
    df["gun"] = _gun_kolonu(df["baslangic"])
    return {
        int(makine_id): np.sort(grp["gun"].to_numpy()) for makine_id, grp in df.groupby("makine_id")
    }


def _bakim_cerceve(gunluk: pd.DataFrame, ariza: pd.DataFrame, pencere: int) -> pd.DataFrame:
    """(makine, gün) başına yuvarlanır-pencere + arıza geçmişi özellikleri."""
    df = gunluk.sort_values(["makine_id", "gun"]).reset_index(drop=True).copy()
    g = df.groupby("makine_id")
    for kaynak, hedef in (
        ("oee", "oee_ort"),
        ("durus_orani", "durus_orani_ort"),
        ("fire_orani", "fire_orani_ort"),
    ):
        df[hedef] = g[kaynak].transform(lambda s: s.rolling(pencere, min_periods=1).mean())
    gunler_map = _ariza_gunleri(ariza)
    sayilar: list[int] = []
    son_gunler: list[float] = []
    for makine_id, gun in zip(df["makine_id"], df["gun"], strict=True):
        tarihler = gunler_map.get(int(makine_id))
        gun64 = pd.Timestamp(gun).to_datetime64()
        if tarihler is None or len(tarihler) == 0:
            sayilar.append(0)
            son_gunler.append(ARIZA_GUN_TAVANI)
            continue
        idx = int(np.searchsorted(tarihler, gun64, side="right"))
        onceki = tarihler[:idx]
        pencere_basi = gun64 - np.timedelta64(30, "D")
        sayilar.append(int((onceki > pencere_basi).sum()))
        if idx == 0:
            son_gunler.append(ARIZA_GUN_TAVANI)
        else:
            gecen = float((gun64 - onceki[-1]) / np.timedelta64(1, "D"))
            son_gunler.append(min(gecen, ARIZA_GUN_TAVANI))
    df["ariza_sayisi_30g"] = sayilar
    df["son_arizadan_gun"] = son_gunler
    return df


def bakim_ozellikleri(
    gunluk: pd.DataFrame, ariza: pd.DataFrame, *, pencere: int = 7, ufuk: int = 7
) -> pd.DataFrame:
    """Kestirimci bakım eğitim çerçevesi: özellikler + ``ariza_var`` etiketi.

    Etiket: makinenin ``(gun, gun+ufuk]`` penceresinde en az bir arızası varsa 1.
    """
    if gunluk.empty:
        return pd.DataFrame(columns=["makine_id", "gun", *BAKIM_OZELLIKLERI, "ariza_var"])
    df = _bakim_cerceve(gunluk, ariza, pencere)
    gunler_map = _ariza_gunleri(ariza)
    etiketler: list[int] = []
    for makine_id, gun in zip(df["makine_id"], df["gun"], strict=True):
        tarihler = gunler_map.get(int(makine_id))
        if tarihler is None or len(tarihler) == 0:
            etiketler.append(0)
            continue
        gun64 = pd.Timestamp(gun).to_datetime64()
        idx = int(np.searchsorted(tarihler, gun64, side="right"))
        sonraki = tarihler[idx:]
        ufuk_sonu = gun64 + np.timedelta64(ufuk, "D")
        etiketler.append(int(len(sonraki) > 0 and sonraki[0] <= ufuk_sonu))
    df["ariza_var"] = etiketler
    return df[["makine_id", "gun", *BAKIM_OZELLIKLERI, "ariza_var"]]


def bakim_guncel_ozellikler(
    gunluk: pd.DataFrame, ariza: pd.DataFrame, *, pencere: int = 7
) -> pd.DataFrame:
    """Çıkarım anı: makine başına son günün özellik satırı (etiketsiz)."""
    if gunluk.empty:
        return pd.DataFrame(columns=["makine_id", "gun", *BAKIM_OZELLIKLERI])
    df = _bakim_cerceve(gunluk, ariza, pencere)
    son = df.groupby("makine_id", as_index=False).tail(1)
    return son[["makine_id", "gun", *BAKIM_OZELLIKLERI]].reset_index(drop=True)


def oee_gecikme_ozellikleri(gunluk: pd.DataFrame, *, gecikme: int = 7) -> pd.DataFrame:
    """OEE regresyonu eğitim çerçevesi: hedef ``oee`` + ``oee_gecikme_1..N`` kolonları."""
    kolonlar = ["makine_id", "gun", "oee"] + [f"oee_gecikme_{k}" for k in range(1, gecikme + 1)]
    if gunluk.empty:
        return pd.DataFrame(columns=kolonlar)
    df = gunluk.sort_values(["makine_id", "gun"])[["makine_id", "gun", "oee"]].copy()
    g = df.groupby("makine_id")
    for k in range(1, gecikme + 1):
        df[f"oee_gecikme_{k}"] = g["oee"].shift(k)
    return df.dropna().reset_index(drop=True)[kolonlar]


def oee_son_pencere(gunluk: pd.DataFrame, *, gecikme: int = 7) -> pd.DataFrame:
    """Çıkarım anı: makine başına en güncel ``gecikme`` OEE değeri (``gecikme_1`` = en yeni).

    Geçmişi ``gecikme`` günden kısa makineler atlanır (tahmin üretilemez).
    """
    kolonlar = ["makine_id", "son_gun"] + [f"oee_gecikme_{k}" for k in range(1, gecikme + 1)]
    if gunluk.empty:
        return pd.DataFrame(columns=kolonlar)
    satirlar: list[dict[str, object]] = []
    for makine_id, grp in gunluk.sort_values(["makine_id", "gun"]).groupby("makine_id"):
        if len(grp) < gecikme:
            continue
        degerler = grp["oee"].tail(gecikme).tolist()[::-1]  # en yeni ilk
        satir: dict[str, object] = {"makine_id": int(makine_id), "son_gun": grp["gun"].iloc[-1]}
        for k in range(1, gecikme + 1):
            satir[f"oee_gecikme_{k}"] = degerler[k - 1]
        satirlar.append(satir)
    return pd.DataFrame(satirlar, columns=kolonlar)


def stok_tuketim_gunluk(hareketler: pd.DataFrame) -> pd.DataFrame:
    """Stok çıkış hareketlerini (malzeme, gün) düzeyinde toplar (tüketim serisi)."""
    kolonlar = ["malzeme_id", "gun", "miktar"]
    if hareketler.empty:
        return pd.DataFrame(columns=kolonlar)
    df = hareketler.copy()
    if "tur" in df.columns:
        df = df[df["tur"] == "cikis"]
    if df.empty:
        return pd.DataFrame(columns=kolonlar)
    df["gun"] = _gun_kolonu(df["zaman"])
    df["miktar"] = df["miktar"].astype(float)
    return (
        df.groupby(["malzeme_id", "gun"], as_index=False)["miktar"]
        .sum()
        .sort_values(["malzeme_id", "gun"])
        .reset_index(drop=True)[kolonlar]
    )
