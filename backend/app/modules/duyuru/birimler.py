"""Duyuru modülü saf sabitleri — beyaz-listeler."""

from __future__ import annotations

# Duyuru önem düzeyi (beyaz-liste).
ONEM_DUZEYLERI: frozenset[str] = frozenset({"bilgi", "uyari", "kritik"})
