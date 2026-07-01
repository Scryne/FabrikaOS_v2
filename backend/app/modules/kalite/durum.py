"""CAPA (uygunsuzluk) durum makinesi — saf (DB'siz) iş kuralı, kapsamlı birim testli.

Yaşam döngüsü (Tam CAPA)::

    acik ─> kok_neden ─> aksiyon_plani ─> uygulama ─> dogrulama ─> kapandi*
      │         │             │              │          │  │
      │         │             │              │          │  └─> uygulama  (doğrulama başarısız)
      └─────────┴─────────────┴──────────────┴──────────┴─> iptal*

``*`` terminal: çıkış geçişi yoktur. Tüm geçişler çağıran katmanda ``kalite:yaz`` iznini
gerektirir (ayrı onay izni yoktur).
"""

from __future__ import annotations

# mevcut durum -> izin verilen hedef durumlar.
GECISLER: dict[str, frozenset[str]] = {
    "acik": frozenset({"kok_neden", "iptal"}),
    "kok_neden": frozenset({"aksiyon_plani", "iptal"}),
    "aksiyon_plani": frozenset({"uygulama", "iptal"}),
    "uygulama": frozenset({"dogrulama", "iptal"}),
    "dogrulama": frozenset({"kapandi", "uygulama", "iptal"}),
    "kapandi": frozenset(),
    "iptal": frozenset(),
}

DURUMLAR: frozenset[str] = frozenset(GECISLER)
TERMINAL_DURUMLAR: frozenset[str] = frozenset({"kapandi", "iptal"})
AKTIF_DURUMLAR: frozenset[str] = DURUMLAR - TERMINAL_DURUMLAR
ILK_DURUM = "acik"


def gecerli_hedefler(mevcut: str) -> frozenset[str]:
    """``mevcut`` durumdan gidilebilecek hedef durumlar (tanımsızsa boş küme)."""
    return GECISLER.get(mevcut, frozenset())


def gecis_gecerli_mi(mevcut: str, hedef: str) -> bool:
    """``mevcut`` → ``hedef`` geçişi durum makinesine göre geçerli mi?"""
    return hedef in gecerli_hedefler(mevcut)
