"""Talep durum makinesi — saf (DB'siz) iş kuralı, birim testli.

Yaşam döngüsü::

    acik ──> inceleniyor ──> cozuldu ──> kapandi*
      │           │            │
      │           │            └──> inceleniyor   (yeniden aç)
      └──> iptal*  inceleniyor ──> iptal*

``*`` terminal: ``kapandi`` ve ``iptal`` çıkışsızdır. Çözülmüş bir talep tekrar
``inceleniyor``a alınabilir (yeniden açma).
"""

from __future__ import annotations

# mevcut durum -> izin verilen hedef durumlar.
GECISLER: dict[str, frozenset[str]] = {
    "acik": frozenset({"inceleniyor", "iptal"}),
    "inceleniyor": frozenset({"cozuldu", "iptal"}),
    "cozuldu": frozenset({"kapandi", "inceleniyor"}),
    "kapandi": frozenset(),
    "iptal": frozenset(),
}

DURUMLAR: frozenset[str] = frozenset(GECISLER)
TERMINAL_DURUMLAR: frozenset[str] = frozenset({"kapandi", "iptal"})
ILK_DURUM = "acik"


def gecerli_hedefler(mevcut: str) -> frozenset[str]:
    """``mevcut`` durumdan gidilebilecek hedef durumlar (tanımsızsa boş küme)."""
    return GECISLER.get(mevcut, frozenset())


def gecis_gecerli_mi(mevcut: str, hedef: str) -> bool:
    """``mevcut`` → ``hedef`` geçişi durum makinesine göre geçerli mi?"""
    return hedef in gecerli_hedefler(mevcut)
