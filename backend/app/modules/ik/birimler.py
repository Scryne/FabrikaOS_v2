"""İK modülü saf sabitleri — beyaz-listeler (DTO/router doğrulamasında kullanılır)."""

from __future__ import annotations

# İzin türleri (beyaz-liste).
IZIN_TURLERI: frozenset[str] = frozenset(
    {"yillik", "mazeret", "hastalik", "ucretsiz", "dogum", "babalik"}
)

# Sunucuda üretilen metinlerin (onay kutusu başlığı) okunur etiketi; ön yüz kendi i18n
# anahtarını (``ik.izin_turu_*``) kullanır. Anahtar kümesi IZIN_TURLERI ile aynı olmalı.
IZIN_TURU_ETIKETLERI: dict[str, str] = {
    "yillik": "yıllık izin",
    "mazeret": "mazeret izni",
    "hastalik": "hastalık izni",
    "ucretsiz": "ücretsiz izin",
    "dogum": "doğum izni",
    "babalik": "babalık izni",
}

# Zimmet (demirbaş atama) durumu.
ZIMMET_DURUMLARI: frozenset[str] = frozenset({"zimmetli", "iade_edildi"})
