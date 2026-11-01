"""Rapor modülü saf sabitleri — tür/biçim/durum beyaz-listeleri + dosya adı."""

from __future__ import annotations

# Desteklenen rapor türleri (beyaz-liste; DTO/router doğrulamasında kullanılır).
# S32: "esg" — dönemsel emisyon ve yoğunluk (esg modülü açık olmalı; router denetler).
RAPOR_TURLERI: frozenset[str] = frozenset({"uretim", "stok", "kalite", "enerji", "isemri", "esg"})

# Desteklenen çıktı biçimleri.
RAPOR_BICIMLERI: frozenset[str] = frozenset({"pdf", "xlsx"})

# Rapor yaşam döngüsü: kuyrukta → hazirlaniyor → hazir | basarisiz (terminal).
RAPOR_DURUMLARI: frozenset[str] = frozenset({"kuyrukta", "hazirlaniyor", "hazir", "basarisiz"})

# Biçim → MIME içerik tipi (indirme yanıtı + nesne deposu üst verisi).
ICERIK_TIPLERI: dict[str, str] = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def rapor_dosya_adi(kod: str, bicim: str) -> str:
    """Rapor dosya adı: ``<kod>.<bicim>`` (ör. ``RP-2026-000001.pdf``)."""
    return f"{kod}.{bicim}"
