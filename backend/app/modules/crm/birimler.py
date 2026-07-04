"""CRM modülü saf sabitleri — beyaz-listeler (DTO/router doğrulamasında kullanılır)."""

from __future__ import annotations

# Firma tipi (beyaz-liste): müşteri, tedarikçi veya her ikisi.
FIRMA_TIPLERI: frozenset[str] = frozenset({"musteri", "tedarikci", "her_ikisi"})
