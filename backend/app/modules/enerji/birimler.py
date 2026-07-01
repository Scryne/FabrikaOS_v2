"""Enerji modülü saf sabitleri — enerji türü beyaz-listesi."""

from __future__ import annotations

# Enerji türleri (beyaz-liste; DTO/router doğrulamasında kullanılır).
ENERJI_TURLERI: frozenset[str] = frozenset({"elektrik", "dogalgaz", "su", "hava", "buhar"})
