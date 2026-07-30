"""Tenant güvenlik ayarlarının sır-güvenli okunması/yazılması (S23 / ADR-0022).

``guvenlik_ayarlari`` JSONB'si OIDC **istemci sırrını** taşır. İki saf kural:

1. **Okumada maskele.** Platform panelinde ayarlar görüntülenebilmeli ama sır düz metin
   dönmemeli — API yanıtında sabit bir maske gösterilir.
2. **Yazmada koru.** Panel maskeyi geri gönderdiğinde (kullanıcı sırra dokunmadı) mevcut
   sır korunur; aksi hâlde her düzenlemede sırrın yeniden yazılması gerekirdi ve boş
   bırakılınca SSO sessizce bozulurdu.

Fonksiyonlar saftır (I/O yok) ve birim testlidir.
"""

from __future__ import annotations

import copy
from typing import Any

# Yanıtta sırrın yerine geçen sabit. Panel bunu aynen geri gönderirse "değiştirme" demektir.
MASKE = "••••••••"


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
