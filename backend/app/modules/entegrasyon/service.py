"""Entegrasyon iş kuralları — anahtar üretimi/özeti/maskeleme + doğrulamalar."""

from __future__ import annotations

import hashlib
import secrets

from app.core.exceptions import DogrulamaHatasi
from app.modules.entegrasyon.birimler import ENTEGRASYON_IZIN_KAPSAMLARI, OLAY_TURU_KATALOGU

ONEK_UZUNLUGU = 12  # görüntü kimliği: anahtarın ilk 12 karakteri (ör. "fos_AbCd1234")


def api_anahtar_uret() -> str:
    """Yeni 3. taraf erişim anahtarı: ``fos_`` + 43 char urlsafe rastgele."""
    return f"fos_{secrets.token_urlsafe(32)}"


def anahtar_ozetle(anahtar: str) -> str:
    """SHA-256 özet (hex) — DB'de düz anahtar yerine bu saklanır ve bununla aranır."""
    return hashlib.sha256(anahtar.encode()).hexdigest()


def kapsamlar_dogrula(izinler: list[str]) -> None:
    """Anahtara yalnız beyaz-listedeki okuma kapsamları atanabilir (en az ayrıcalık)."""
    bilinmeyen = sorted(set(izinler) - set(ENTEGRASYON_IZIN_KAPSAMLARI))
    if bilinmeyen:
        raise DogrulamaHatasi(
            "Geçersiz anahtar kapsamı",
            detaylar=[
                {
                    "alan": "izinler",
                    "mesaj": f"Bilinmeyen: {', '.join(bilinmeyen)} — "
                    f"geçerli: {', '.join(sorted(ENTEGRASYON_IZIN_KAPSAMLARI))}",
                }
            ],
        )


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
