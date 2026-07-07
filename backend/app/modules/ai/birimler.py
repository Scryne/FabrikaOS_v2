"""AI modülü saf sabitleri — model türleri, eğitim durumları, risk seviyesi eşlemesi."""

from __future__ import annotations

# Desteklenen model türleri (beyaz-liste; DTO/router doğrulamasında kullanılır).
MODEL_TURLERI: frozenset[str] = frozenset({"kestirimci_bakim", "anomali", "oee", "stok"})

# Model kaydı yaşam döngüsü: egitiliyor → hazir | basarisiz (terminal).
MODEL_DURUMLARI: frozenset[str] = frozenset({"egitiliyor", "hazir", "basarisiz"})

# Kestirimci bakım risk seviyeleri (skor ∈ [0, 1] olasılığından türetilir).
RISK_SEVIYELERI: frozenset[str] = frozenset({"dusuk", "orta", "yuksek"})

_ESIK_ORTA = 0.33
_ESIK_YUKSEK = 0.66


def risk_seviyesi(skor: float) -> str:
    """Risk skorunu (arıza olasılığı, 0–1) seviyeye eşler. Aralık dışı → ``ValueError``."""
    if not 0.0 <= skor <= 1.0:
        raise ValueError(f"Risk skoru [0, 1] aralığında olmalı: {skor!r}")
    if skor >= _ESIK_YUKSEK:
        return "yuksek"
    if skor >= _ESIK_ORTA:
        return "orta"
    return "dusuk"
