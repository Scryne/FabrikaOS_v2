"""İK modülü saf sabitleri — beyaz-listeler (DTO/router doğrulamasında kullanılır)."""

from __future__ import annotations

# İzin türleri (beyaz-liste).
IZIN_TURLERI: frozenset[str] = frozenset(
    {"yillik", "mazeret", "hastalik", "ucretsiz", "dogum", "babalik"}
)

# Zimmet (demirbaş atama) durumu.
ZIMMET_DURUMLARI: frozenset[str] = frozenset({"zimmetli", "iade_edildi"})
