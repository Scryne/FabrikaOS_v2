"""İzin talebi durum makinesi — saf (DB'siz) iş kuralı, kapsamlı birim testli.

Yaşam döngüsü (satınalma onay akışının aynası)::

    taslak ──> onay_bekliyor ──> onaylandi*
       │            │
       │            └──────────> reddedildi*
       └──> iptal*   onay_bekliyor ──> iptal*

``*`` terminal: çıkış geçişi yoktur. ``onaylandi``/``reddedildi`` hedefleri çağıran
katmanda ``ik:onay`` iznini gerektirir (görev ayrımı; kural durum tablosunda değil router'da).
"""

from __future__ import annotations

# mevcut durum -> izin verilen hedef durumlar.
GECISLER: dict[str, frozenset[str]] = {
    "taslak": frozenset({"onay_bekliyor", "iptal"}),
    "onay_bekliyor": frozenset({"onaylandi", "reddedildi", "iptal"}),
    "onaylandi": frozenset(),
    "reddedildi": frozenset(),
    "iptal": frozenset(),
}

DURUMLAR: frozenset[str] = frozenset(GECISLER)
TERMINAL_DURUMLAR: frozenset[str] = frozenset({"onaylandi", "reddedildi", "iptal"})
ILK_DURUM = "taslak"


def gecerli_hedefler(mevcut: str) -> frozenset[str]:
    """``mevcut`` durumdan gidilebilecek hedef durumlar (tanımsızsa boş küme)."""
    return GECISLER.get(mevcut, frozenset())


def gecis_gecerli_mi(mevcut: str, hedef: str) -> bool:
    """``mevcut`` → ``hedef`` geçişi durum makinesine göre geçerli mi?"""
    return hedef in gecerli_hedefler(mevcut)
