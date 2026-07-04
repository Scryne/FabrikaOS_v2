"""İSG modülü saf sabitleri — beyaz-listeler (DTO/router doğrulamasında kullanılır)."""

from __future__ import annotations

# İş kazası kaydı türü: kaza (yaralanmalı), ramak-kala (yaralanmasız olay), meslek hastalığı.
KAZA_TURLERI: frozenset[str] = frozenset({"kaza", "ramak_kala", "meslek_hastaligi"})

# Kaza ağırlık derecesi (İSG raporlama).
KAZA_AGIRLIKLARI: frozenset[str] = frozenset({"hafif", "orta", "agir", "olumcul"})

# Risk değerlendirme durum akışı (basit yaşam döngüsü, ayrı durum makinesi gerekmez).
RISK_DURUMLARI: frozenset[str] = frozenset({"acik", "devam", "kapandi"})
