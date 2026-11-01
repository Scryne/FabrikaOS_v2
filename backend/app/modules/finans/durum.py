"""Fatura durum makinesi — saf (DB'siz) iş kuralı, birim testli (S29, ADR-0048).

Yaşam döngüsü::

    taslak ──> onay_bekliyor ──> kesildi ──> kapandi*
      ▲  │           │              │
      │  └─> iptal*  ├──> taslak    └──> iptal*   (yalnız hiç ödeme/tahsilat yoksa)
      └──────────────┘    (iade: düzeltilip yeniden gönderilir)

``*`` terminal. ``kesildi`` cari hesaba işler; ``kapandi`` ödenen/tahsil edilen tutar genel toplama
ulaşınca kendiliğinden olur (elle geçilmez). ``kesildi`` ve iade çağıran katmanda ``finans:onay``
ister ve faturayı hazırlayan kişi kesemez (görev ayrımı).
"""

from __future__ import annotations

GECISLER: dict[str, frozenset[str]] = {
    "taslak": frozenset({"onay_bekliyor", "iptal"}),
    "onay_bekliyor": frozenset({"kesildi", "taslak", "iptal"}),
    "kesildi": frozenset({"kapandi", "iptal"}),
    "kapandi": frozenset(),
    "iptal": frozenset(),
}

DURUMLAR: frozenset[str] = frozenset(GECISLER)
TERMINAL_DURUMLAR: frozenset[str] = frozenset({"kapandi", "iptal"})
ILK_DURUM = "taslak"
# Elle istenemeyen hedef: yalnız ödeme/tahsilat uygulanırken servis geçirir.
OTOMATIK_HEDEFLER: frozenset[str] = frozenset({"kapandi"})


def gecerli_hedefler(mevcut: str) -> frozenset[str]:
    """``mevcut`` durumdan gidilebilecek hedef durumlar (tanımsızsa boş küme)."""
    return GECISLER.get(mevcut, frozenset())


def gecis_gecerli_mi(mevcut: str, hedef: str) -> bool:
    """``mevcut`` → ``hedef`` geçişi durum makinesine göre geçerli mi?"""
    return hedef in gecerli_hedefler(mevcut)
