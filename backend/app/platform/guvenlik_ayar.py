"""Tenant güvenlik ayarlarının sır-güvenli okunması/yazılması (S23 / ADR-0022).

``guvenlik_ayarlari`` JSONB'si OIDC **istemci sırrını** taşır. Üç saf kural:

1. **Okumada maskele.** Platform panelinde ayarlar görüntülenebilmeli ama sır düz metin
   dönmemeli — API yanıtında sabit bir maske gösterilir.
2. **Yazmada koru.** Panel maskeyi geri gönderdiğinde (kullanıcı sırra dokunmadı) mevcut
   sır korunur; aksi hâlde her düzenlemede sırrın yeniden yazılması gerekirdi ve boş
   bırakılınca SSO sessizce bozulurdu.
3. **Debug logunu süreli aç.** ``debug_claim_log`` ham ID token claim'lerini (e-posta,
   ad, grup üyeliği = **kişisel veri**) sunucu loguna yazar. Açılışta
   ``debug_claim_log_bitis`` damgalanır; süre dolunca log kendiliğinden susar. Açma/kapama
   geçişi çağırana bildirilir, o da denetim izine yazar.

Fonksiyonlar saftır (I/O yok) ve birim testlidir.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

# Yanıtta sırrın yerine geçen sabit. Panel bunu aynen geri gönderirse "değiştirme" demektir.
MASKE = "••••••••"

# Ham claim logunun azami ömrü. Teşhis için yeterli, PII birikimi için kısa.
DEBUG_OMRU_DK = 60


def ayarlari_maskele(ayarlar: dict[str, Any] | None) -> dict[str, Any] | None:
    """Yanıt için kopya üretir; OIDC istemci sırrı varsa maskeyle değiştirir."""
    if not isinstance(ayarlar, dict):
        return None
    kopya = copy.deepcopy(ayarlar)
    oidc = kopya.get("oidc")
    if isinstance(oidc, dict) and oidc.get("istemci_sirri"):
        oidc["istemci_sirri"] = MASKE
    return kopya


def sirri_koru(yeni: dict[str, Any] | None, mevcut: dict[str, Any] | None) -> dict[str, Any] | None:
    """Gelen ayarlarda sır maskeli/boş ise mevcut sırrı taşır (kopya döner).

    ``yeni`` ``None`` ise (varsayılana dön) hiçbir şey taşınmaz: SSO da kapanır.
    """
    if not isinstance(yeni, dict):
        return None
    kopya = copy.deepcopy(yeni)
    gelen_oidc = kopya.get("oidc")
    if not isinstance(gelen_oidc, dict):
        return kopya

    mevcut_oidc = mevcut.get("oidc") if isinstance(mevcut, dict) else None
    mevcut_sir = mevcut_oidc.get("istemci_sirri") if isinstance(mevcut_oidc, dict) else None
    gelen_sir = gelen_oidc.get("istemci_sirri")
    if (not gelen_sir or gelen_sir == MASKE) and mevcut_sir:
        gelen_oidc["istemci_sirri"] = mevcut_sir
    return kopya


@dataclass(frozen=True, slots=True)
class DebugGecisi:
    """Ham claim logunun bu yazmadaki durum değişimi (denetim izi için)."""

    acildi: bool = False
    kapandi: bool = False
    bitis: datetime | None = None


def _debug_bitisi(ayarlar: dict[str, Any] | None) -> datetime | None:
    oidc = ayarlar.get("oidc") if isinstance(ayarlar, dict) else None
    if not isinstance(oidc, dict) or not oidc.get("debug_claim_log"):
        return None
    ham = oidc.get("debug_claim_log_bitis")
    if not ham:
        return None
    try:
        an = datetime.fromisoformat(str(ham))
    except ValueError:
        return None
    return an if an.tzinfo else an.replace(tzinfo=UTC)


def debug_suresini_damgala(
    yeni: dict[str, Any] | None,
    mevcut: dict[str, Any] | None,
    *,
    simdi: datetime | None = None,
) -> tuple[dict[str, Any] | None, DebugGecisi]:
    """Debug logu açıldıysa bitiş damgası basar, kapandıysa temizler (kopya döner).

    - Kapalıyken açılırsa: ``simdi + DEBUG_OMRU_DK`` damgalanır, ``acildi=True``.
    - Zaten açık ve süresi geçmemişse: **mevcut damga korunur** — ilgisiz bir ayar
      düzenlemesi (ör. IP listesi) debug penceresini sessizce uzatmasın.
    - Açıkken kapatılır/süresi geçmiş olarak gelirse: damga silinir, ``kapandi=True``.
    """
    an = simdi or datetime.now(UTC)
    onceki_bitis = _debug_bitisi(mevcut)
    onceki_aktif = onceki_bitis is not None and an < onceki_bitis

    if not isinstance(yeni, dict):
        return None, DebugGecisi(kapandi=onceki_aktif)

    kopya = copy.deepcopy(yeni)
    oidc = kopya.get("oidc")
    if not isinstance(oidc, dict):
        return kopya, DebugGecisi(kapandi=onceki_aktif)

    if not oidc.get("debug_claim_log"):
        oidc.pop("debug_claim_log_bitis", None)
        return kopya, DebugGecisi(kapandi=onceki_aktif)

    if onceki_aktif and onceki_bitis is not None:
        oidc["debug_claim_log_bitis"] = onceki_bitis.isoformat()
        return kopya, DebugGecisi(bitis=onceki_bitis)

    bitis = an + timedelta(minutes=DEBUG_OMRU_DK)
    oidc["debug_claim_log_bitis"] = bitis.isoformat()
    return kopya, DebugGecisi(acildi=True, bitis=bitis)
