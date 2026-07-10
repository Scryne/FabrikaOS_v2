"""Entegrasyon iş kuralları — anahtar maskeleme + doğrulamalar."""

from __future__ import annotations

from app.core.exceptions import DogrulamaHatasi
from app.modules.entegrasyon.birimler import OLAY_TURU_KATALOGU


def anahtar_maskele(anahtar: str) -> str:
    """Gizli değeri görüntü için maskeler: ilk 8 + son 4 karakter (``whs_abcd…wxyz``)."""
    if len(anahtar) <= 12:
        return "****"
    return f"{anahtar[:8]}…{anahtar[-4:]}"


def olay_turleri_dogrula(turler: list[str]) -> None:
    """Katalog dışı olay türünü reddeder (yazım hatası sessizce ölü abonelik üretmesin)."""
    bilinmeyen = sorted(set(turler) - set(OLAY_TURU_KATALOGU))
    if bilinmeyen:
        raise DogrulamaHatasi(
            "Katalogda olmayan olay türü",
            detaylar=[
                {
                    "alan": "olay_turleri",
                    "mesaj": f"Bilinmeyen: {', '.join(bilinmeyen)} — "
                    f"geçerli: {', '.join(sorted(OLAY_TURU_KATALOGU))}",
                }
            ],
        )


def url_dogrula(url: str) -> None:
    """Hedef URL politikası: ``https://`` zorunlu; yalnız yerel geliştirme/test alıcıları
    için ``http://localhost`` ve ``http://127.0.0.1`` serbesttir."""
    if url.startswith("https://"):
        return
    if url.startswith(("http://localhost", "http://127.0.0.1")):
        return
    raise DogrulamaHatasi(
        "Webhook URL'i https olmalı",
        detaylar=[
            {"alan": "url", "mesaj": "https:// (veya yerel testte http://localhost) gerekli"}
        ],
    )
