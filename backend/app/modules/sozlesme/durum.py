"""Sözleşme durum makinesi — saf (DB'siz) iş kuralı, birim testli.

Yaşam döngüsü::

    taslak ──> aktif ──> sonlandi*
       │         │
       │         └──────> feshedildi*
       └──> iptal*   aktif ──> iptal*

``*`` terminal: çıkış geçişi yoktur. ``sonlandi`` sözleşmenin süresi/kapsamı tamamlanarak
bittiğini, ``feshedildi`` erken/tek taraflı sonlandırmayı, ``iptal`` hiç yürürlüğe girmeden
vazgeçilmesini ifade eder.
"""

from __future__ import annotations

# mevcut durum -> izin verilen hedef durumlar.
GECISLER: dict[str, frozenset[str]] = {
    "taslak": frozenset({"aktif", "iptal"}),
    "aktif": frozenset({"sonlandi", "feshedildi", "iptal"}),
    "sonlandi": frozenset(),
    "feshedildi": frozenset(),
    "iptal": frozenset(),
}

DURUMLAR: frozenset[str] = frozenset(GECISLER)
TERMINAL_DURUMLAR: frozenset[str] = frozenset({"sonlandi", "feshedildi", "iptal"})
ILK_DURUM = "taslak"


def gecerli_hedefler(mevcut: str) -> frozenset[str]:
    """``mevcut`` durumdan gidilebilecek hedef durumlar (tanımsızsa boş küme)."""
    return GECISLER.get(mevcut, frozenset())


def gecis_gecerli_mi(mevcut: str, hedef: str) -> bool:
    """``mevcut`` → ``hedef`` geçişi durum makinesine göre geçerli mi?"""
    return hedef in gecerli_hedefler(mevcut)
