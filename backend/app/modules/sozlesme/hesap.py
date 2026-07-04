"""Sözleşme saf hesapları — yaklaşan bitiş tespiti (DB'siz, birim testli)."""

from __future__ import annotations

from datetime import date


def kalan_gun(bitis: date, bugun: date) -> int:
    """``bugun`` ile ``bitis`` arasındaki gün farkı (geçmişte ise negatif)."""
    return (bitis - bugun).days


def yaklasiyor_mu(bitis: date, bugun: date, esik_gun: int) -> bool:
    """Sözleşme bitişine ``esik_gun`` veya daha az (ve 0'dan büyük eşit) kaldı mı?

    Bitiş bugüne eşit veya ileri (kalan ≥ 0) **ve** eşik gün içinde (kalan ≤ esik_gun)
    ise yaklaşıyor sayılır. Süresi geçmiş sözleşmeler (kalan < 0) bu tanıma girmez.
    """
    kalan = kalan_gun(bitis, bugun)
    return 0 <= kalan <= esik_gun
