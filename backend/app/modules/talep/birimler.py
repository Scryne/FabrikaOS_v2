"""Talep modülü saf sabitleri — beyaz-listeler."""

from __future__ import annotations

# Talep türü (beyaz-liste).
TALEP_TURLERI: frozenset[str] = frozenset({"teklif", "destek", "sikayet", "bilgi", "diger"})

# Talep önceliği (beyaz-liste).
ONCELIKLER: frozenset[str] = frozenset({"dusuk", "orta", "yuksek"})
