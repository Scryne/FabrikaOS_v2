"""Model artefakt deposu — joblib serileştirme ↔ nesne depolama (sürümlü, tenant-izole).

DYS'nin ``NesneDepo`` soyutlaması yeniden kullanılır (MinIO gerçek, ``BellekNesneDepo``
test). Anahtar öneki ``tenant_<slug>/model/...`` olduğundan artefaktlar da tenant-izoledir
(S12 belge deseni). Çağrılar senkrondur; async katman ``asyncio.to_thread`` ile sarar.

Süreç-içi önbellek: aynı anahtar (slug+tur+surum tekil) ikinci kez diskten/S3'ten
yüklenmez. Yeni eğitim yeni sürüm ürettiğinden önbellek bayatlamaz (anahtar değişir).
"""

from __future__ import annotations

import io
from typing import Any

import joblib

from app.modules.dys.depolama import nesne_depo_al

_ICERIK_TIPI = "application/octet-stream"

_onbellek: dict[str, Any] = {}


def model_nesne_anahtari(slug: str, tur: str, surum: int) -> str:
    """Tenant-izole artefakt anahtarı: ``tenant_<slug>/model/<tur>/<surum>/model.joblib``."""
    return f"tenant_{slug}/model/{tur}/{surum}/model.joblib"


def artefakt_kaydet(anahtar: str, nesne: Any) -> int:
    """Model nesnesini joblib ile serileştirip depoya yazar; bayt boyutunu döndürür."""
    tampon = io.BytesIO()
    joblib.dump(nesne, tampon)
    veri = tampon.getvalue()
    nesne_depo_al().yukle(anahtar, veri, _ICERIK_TIPI)
    return len(veri)


def artefakt_yukle(anahtar: str) -> Any:
    """Artefaktı depodan okuyup model nesnesine geri çevirir (önbelleksiz)."""
    veri = nesne_depo_al().indir(anahtar)
    return joblib.load(io.BytesIO(veri))


def artefakt_yukle_onbellekli(anahtar: str) -> Any:
    """Önbellekli yükleme — aynı sürüm süreç ömrü boyunca bir kez indirilir."""
    if anahtar not in _onbellek:
        _onbellek[anahtar] = artefakt_yukle(anahtar)
    return _onbellek[anahtar]


def onbellek_temizle() -> None:
    """Süreç-içi model önbelleğini boşaltır (testler için)."""
    _onbellek.clear()
