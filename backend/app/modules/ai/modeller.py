"""AI model katmanı (saf scikit-learn) — dört modelin eğit/tahmin çiftleri.

Tümü saftır (DB/IO yok) ve **deterministiktir** (``random_state=42``):

- ``kestirimci_bakim`` — RandomForestClassifier; makine başına "önümüzdeki ufukta arıza"
  olasılığı (risk skoru + seviye).
- ``anomali`` — IsolationForest; makine-gün gözlemlerinde aykırılık (skor küçüldükçe
  daha aykırı).
- ``oee`` — Ridge (gecikme özellikleri); makine başına özyinelemeli OEE ufuk tahmini.
- ``stok`` — malzeme başına lineer tüketim hızı (kümülatif tüketime en küçük kareler);
  kalan gün + önerilen sipariş.

Eğitim fonksiyonları az veride ``YetersizVeri`` yükseltir (servis kaydı ``basarisiz``
yapar). Tahmin fonksiyonları **JSON-serileştirilebilir** ``list[dict]`` döndürür.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LinearRegression, Ridge

from app.modules.ai.birimler import risk_seviyesi
from app.modules.ai.ozellikler import ANOMALI_OZELLIKLERI, BAKIM_OZELLIKLERI

RANDOM_STATE = 42

# Eğitim için gereken en az gözlem (makine-gün / lag satırı).
MIN_SATIR = 14

# Malzeme başına tüketim hızı kestirimi için gereken en az gün.
MIN_STOK_GUN = 3


class YetersizVeri(Exception):
    """Model eğitimi için yeterli tenant verisi yok."""


@dataclass(frozen=True, slots=True)
class EgitimSonucu:
    """Eğitilmiş model nesnesi (serileştirilecek) + eğitim metrikleri."""

    nesne: Any
    metrikler: dict[str, float | int]


def _satir_kontrol(df: pd.DataFrame, gerekli: int = MIN_SATIR) -> None:
    if len(df) < gerekli:
        raise YetersizVeri(f"En az {gerekli} gözlem gerekli (eldeki: {len(df)})")


# --- kestirimci bakım ---
def kestirimci_bakim_egit(df: pd.DataFrame) -> EgitimSonucu:
    """``bakim_ozellikleri`` çerçevesinden arıza sınıflandırıcısı eğitir."""
    _satir_kontrol(df)
    x = df[BAKIM_OZELLIKLERI]
    y = df["ariza_var"].astype(int)
    model = RandomForestClassifier(
        n_estimators=100, random_state=RANDOM_STATE, class_weight="balanced"
    )
    model.fit(x, y)
    return EgitimSonucu(
        nesne=model,
        metrikler={
            "satir_sayisi": int(len(df)),
            "dogruluk": round(float(model.score(x, y)), 4),
            "pozitif_oran": round(float(y.mean()), 4),
        },
    )


def _pozitif_olasilik(model: Any, x: pd.DataFrame) -> np.ndarray:
    """Sınıf 1 (arıza) olasılığı; model hiç arıza görmediyse 0 vektörü."""
    siniflar = list(model.classes_)
    if 1 not in siniflar:
        return np.zeros(len(x))
    return np.asarray(model.predict_proba(x))[:, siniflar.index(1)]


def kestirimci_bakim_tahmin(nesne: Any, guncel: pd.DataFrame) -> list[dict[str, Any]]:
    """Makine başına risk skoru + seviye (riski yüksek olan önce)."""
    if guncel.empty:
        return []
    olasiliklar = _pozitif_olasilik(nesne, guncel[BAKIM_OZELLIKLERI])
    sonuclar = [
        {
            "makine_id": int(satir.makine_id),
            "veri_gunu": pd.Timestamp(satir.gun).date().isoformat(),
            "risk_skoru": round(float(p), 4),
            "seviye": risk_seviyesi(float(p)),
        }
        for satir, p in zip(guncel.itertuples(), olasiliklar, strict=True)
    ]
    return sorted(sonuclar, key=lambda s: s["risk_skoru"], reverse=True)


# --- anomali ---
def anomali_egit(gunluk: pd.DataFrame) -> EgitimSonucu:
    """Günlük makine özetinden IsolationForest eğitir."""
    _satir_kontrol(gunluk)
    x = gunluk[ANOMALI_OZELLIKLERI]
    model = IsolationForest(n_estimators=100, contamination=0.05, random_state=RANDOM_STATE)
    model.fit(x)
    return EgitimSonucu(nesne=model, metrikler={"satir_sayisi": int(len(gunluk))})


def anomali_tahmin(nesne: Any, gunluk: pd.DataFrame) -> list[dict[str, Any]]:
    """Aykırı makine-gün gözlemleri (en aykırı — en düşük skor — önce)."""
    if gunluk.empty:
        return []
    x = gunluk[ANOMALI_OZELLIKLERI]
    etiketler = nesne.predict(x)  # -1 = aykırı
    skorlar = nesne.decision_function(x)
    bulgular = [
        {
            "makine_id": int(satir.makine_id),
            "gun": pd.Timestamp(satir.gun).date().isoformat(),
            "skor": round(float(skor), 4),
            **{alan: round(float(getattr(satir, alan)), 4) for alan in ANOMALI_OZELLIKLERI},
        }
        for satir, etiket, skor in zip(gunluk.itertuples(), etiketler, skorlar, strict=True)
        if etiket == -1
    ]
    return sorted(bulgular, key=lambda b: b["skor"])


# --- OEE tahmini ---
def oee_egit(lagli: pd.DataFrame, *, gecikme: int = 7) -> EgitimSonucu:
    """Gecikme çerçevesinden Ridge regresyonu eğitir (nesne gecikmeyi de taşır)."""
    _satir_kontrol(lagli)
    kolonlar = [f"oee_gecikme_{k}" for k in range(1, gecikme + 1)]
    x = lagli[kolonlar]
    y = lagli["oee"]
    model = Ridge(alpha=1.0)
    model.fit(x, y)
    tahmin = model.predict(x)
    return EgitimSonucu(
        nesne={"model": model, "gecikme": gecikme},
        metrikler={
            "satir_sayisi": int(len(lagli)),
            "r2": round(float(model.score(x, y)), 4),
            "mae": round(float(np.abs(np.asarray(y) - tahmin).mean()), 4),
        },
    )


def oee_tahmin(nesne: Any, son: pd.DataFrame, *, ufuk: int = 7) -> list[dict[str, Any]]:
    """Makine başına özyinelemeli ``ufuk`` günlük OEE tahmini ([0, 1] aralığına kırpılır)."""
    if son.empty:
        return []
    model = nesne["model"]
    gecikme = int(nesne["gecikme"])
    kolonlar = [f"oee_gecikme_{k}" for k in range(1, gecikme + 1)]
    sonuclar: list[dict[str, Any]] = []
    for satir in son.itertuples():
        pencere = [float(getattr(satir, k)) for k in kolonlar]  # [0] = en yeni
        son_gun = pd.Timestamp(satir.son_gun)
        noktalar: list[dict[str, Any]] = []
        for k in range(1, ufuk + 1):
            girdi = pd.DataFrame([dict(zip(kolonlar, pencere, strict=True))])
            deger = float(np.clip(model.predict(girdi)[0], 0.0, 1.0))
            noktalar.append(
                {"gun": (son_gun + pd.Timedelta(days=k)).date().isoformat(), "oee": round(deger, 4)}
            )
            pencere = [deger, *pencere[:-1]]
        sonuclar.append({"makine_id": int(satir.makine_id), "tahminler": noktalar})
    return sonuclar


# --- stok ihtiyaç ---
def stok_egit(tuketim: pd.DataFrame) -> EgitimSonucu:
    """Malzeme başına günlük tüketim hızını kümülatif seriye en küçük karelerle oturtur."""
    hizlar: dict[int, float] = {}
    for malzeme_id, grp in tuketim.groupby("malzeme_id"):
        grp = grp.sort_values("gun")
        if len(grp) < MIN_STOK_GUN:
            continue
        gunler = (grp["gun"] - grp["gun"].iloc[0]).dt.days.to_numpy(dtype=float).reshape(-1, 1)
        kumulatif = grp["miktar"].cumsum().to_numpy(dtype=float)
        model = LinearRegression()
        model.fit(gunler, kumulatif)
        hiz = float(model.coef_[0])
        if hiz > 0:
            hizlar[int(malzeme_id)] = hiz
    if not hizlar:
        raise YetersizVeri(
            f"Hiçbir malzemede yeterli tüketim geçmişi yok (malzeme başına ≥{MIN_STOK_GUN} gün)"
        )
    return EgitimSonucu(
        nesne={"hizlar": hizlar},
        metrikler={"malzeme_sayisi": len(hizlar), "satir_sayisi": int(len(tuketim))},
    )


def stok_tahmin(nesne: Any, malzemeler: pd.DataFrame) -> list[dict[str, Any]]:
    """Malzeme başına kalan gün + önerilen sipariş (en kritik önce).

    Tüketim geçmişi olmayan (modelde hızı bulunmayan) malzemeler atlanır.
    """
    if malzemeler.empty:
        return []
    hizlar: dict[int, float] = nesne["hizlar"]
    sonuclar: list[dict[str, Any]] = []
    for satir in malzemeler.itertuples():
        hiz = hizlar.get(int(satir.malzeme_id))
        if hiz is None or hiz <= 0:
            continue
        mevcut = float(satir.mevcut_miktar)
        sonuclar.append(
            {
                "malzeme_id": int(satir.malzeme_id),
                "kod": str(satir.kod),
                "ad": str(satir.ad),
                "birim": str(satir.birim),
                "mevcut_miktar": round(mevcut, 3),
                "kritik_stok": round(float(satir.kritik_stok), 3),
                "gunluk_tuketim": round(hiz, 3),
                "kalan_gun": round(mevcut / hiz, 1),
                "onerilen_siparis": round(max(0.0, hiz * 30.0 - mevcut), 2),
            }
        )
    return sorted(sonuclar, key=lambda s: s["kalan_gun"])
