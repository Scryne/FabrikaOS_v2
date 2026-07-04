"""Sözleşme modülü saf sabitleri — beyaz-listeler."""

from __future__ import annotations

# Sözleşme türü (beyaz-liste).
SOZLESME_TURLERI: frozenset[str] = frozenset({"satis", "alis", "hizmet", "nda", "kira", "diger"})
