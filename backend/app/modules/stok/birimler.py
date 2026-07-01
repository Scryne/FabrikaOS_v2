"""Stok modülü saf sabitleri — ölçü birimleri ve hareket türleri (beyaz-liste)."""

from __future__ import annotations

# Desteklenen ölçü birimleri (beyaz-liste; DTO/router doğrulamasında kullanılır).
BIRIMLER: frozenset[str] = frozenset(
    {
        "adet",
        "kg",
        "gram",
        "litre",
        "mililitre",
        "metre",
        "santimetre",
        "paket",
        "kutu",
        "koli",
        "ton",
        "rulo",
    }
)

# Stok hareketi türleri: giriş (+), çıkış (−), düzeltme (mutlak sayım sonucu).
STOK_HAREKET_TURLERI: frozenset[str] = frozenset({"giris", "cikis", "duzeltme"})
