"""Risk değerlendirme matrisi — saf (DB'siz) iş kuralı, kapsamlı birim testli.

5×5 risk matrisi: ``risk_skoru = olasilik × siddet`` (her ikisi 1..5). Skor eşiklerinden
risk seviyesi türetilir::

    skor  1–4  → dusuk
    skor  5–9  → orta
    skor 10–15 → yuksek
    skor 16–25 → cok_yuksek

Değerlendirme girişleri (olasılık/şiddet) DTO/router katmanında bu fonksiyonlarla doğrulanır;
``risk_skoru`` ve ``risk_seviyesi`` kayıt yazımında sunucuda hesaplanır (istemciye güvenilmez).
"""

from __future__ import annotations

RISK_SEVIYELERI: frozenset[str] = frozenset({"dusuk", "orta", "yuksek", "cok_yuksek"})

# (üst_sınır_dahil, seviye) — artan skor sırasında ilk eşleşen seviye kullanılır.
_ESIKLER: tuple[tuple[int, str], ...] = (
    (4, "dusuk"),
    (9, "orta"),
    (15, "yuksek"),
    (25, "cok_yuksek"),
)


def _aralikta(deger: int, ad: str) -> None:
    if not 1 <= deger <= 5:
        raise ValueError(f"{ad} 1..5 aralığında olmalı (verilen: {deger})")


def risk_skoru(olasilik: int, siddet: int) -> int:
    """``olasilik × siddet`` (her ikisi 1..5); aralık dışı değer ``ValueError`` fırlatır."""
    _aralikta(olasilik, "olasilik")
    _aralikta(siddet, "siddet")
    return olasilik * siddet


def risk_seviyesi(skor: int) -> str:
    """Risk skorundan (1..25) risk seviyesini döndürür."""
    for ust, seviye in _ESIKLER:
        if skor <= ust:
            return seviye
    return "cok_yuksek"
