"""Satış siparişi durum makinesi — saf (DB'siz) iş kuralı (S31, ADR-0050).

Yaşam döngüsü::

    taslak ──> onaylandi ──> sevk_edildi ──> kapandi*
       │           │
       └──> iptal* └──> iptal*

``*`` terminal. ``onaylandi`` geçişi MRP'yi tetikler (iş emri + satınalma talebi) ve
``satis:onay`` ister; siparişi açan kişi onaylayamaz (görev ayrımı, router/servis katmanında).
Onaylı sipariş iptal edilirse tetiklenen iş emirleri ve talepler kendiliğinden kapanmaz: onlar
kendi sahiplerinin kararıdır (iptal yanıtı açık kalanları listeler).
"""

from __future__ import annotations

GECISLER: dict[str, frozenset[str]] = {
    "taslak": frozenset({"onaylandi", "iptal"}),
    "onaylandi": frozenset({"sevk_edildi", "iptal"}),
    "sevk_edildi": frozenset({"kapandi"}),
    "kapandi": frozenset(),
    "iptal": frozenset(),
}

DURUMLAR: frozenset[str] = frozenset(GECISLER)
TERMINAL_DURUMLAR: frozenset[str] = frozenset({"kapandi", "iptal"})
ILK_DURUM = "taslak"
# Yalnız taslakta kalemler değişebilir: onaydan sonra MRP tetikleri kalemlere bağlıdır.
DUZENLENEBILIR: frozenset[str] = frozenset({"taslak"})


def gecerli_hedefler(mevcut: str) -> frozenset[str]:
    return GECISLER.get(mevcut, frozenset())


def gecis_gecerli_mi(mevcut: str, hedef: str) -> bool:
    return hedef in gecerli_hedefler(mevcut)
