"""İş emri durum makinesi — saf (DB'siz) iş kuralı, kapsamlı birim testli.

Yaşam döngüsü::

    acik ──> atandi ──> devam_ediyor ──> kapandi*
      │        │            │
      └────────┴────────────┴──> iptal*

``*`` terminal: çıkış geçişi yoktur (yeniden açma yok). Geçersiz geçiş çağıran
katmanda 409 Çakışma'ya dönüşür. ``atandi``'ya geçiş ``atanan_kullanici_id``
gerektirir; bu kural servis katmanında (422) uygulanır, durum tablosunda değil.
"""

from __future__ import annotations

# mevcut durum -> izin verilen hedef durumlar.
GECISLER: dict[str, frozenset[str]] = {
    "acik": frozenset({"atandi", "iptal"}),
    "atandi": frozenset({"devam_ediyor", "iptal"}),
    "devam_ediyor": frozenset({"kapandi", "iptal"}),
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
