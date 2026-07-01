"""Kalite modülü saf sabitleri — beyaz-listeler (DTO/router doğrulamasında kullanılır)."""

from __future__ import annotations

# Kalite kontrol türü (denetim bağlamı).
KONTROL_TURLERI: frozenset[str] = frozenset({"uretim", "giris", "final"})

# Kalite kontrol sonucu.
KONTROL_SONUCLARI: frozenset[str] = frozenset({"gecti", "kaldi", "sartli"})

# Uygunsuzluk önem derecesi.
UYGUNSUZLUK_ONEMLERI: frozenset[str] = frozenset({"dusuk", "orta", "yuksek", "kritik"})

# CAPA aksiyon türü: düzeltici (corrective) / önleyici (preventive).
CAPA_AKSIYON_TURLERI: frozenset[str] = frozenset({"duzeltici", "onleyici"})

# CAPA aksiyon durumu (aksiyon başına, ana uygunsuzluk durumundan bağımsız).
CAPA_AKSIYON_DURUMLARI: frozenset[str] = frozenset({"planlandi", "tamamlandi", "iptal"})
