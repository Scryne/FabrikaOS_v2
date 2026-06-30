"""CSV → OlcumPaketi ayrıştırma. Başlık satırı zorunlu; kolon adları OlcumPaketi alanları.

Beklenen kolonlar: makine_kod, zaman (ISO-8601), vardiya, planlanan_sure_dk, durus_sure_dk,
toplam_adet, saglam_adet, ideal_cevrim_sn. ``olcum_id`` yoksa satırdan deterministik
üretilir (aynı CSV iki kez yüklenirse idempotent kalır).
"""

from __future__ import annotations

import csv
import io
import uuid

from pydantic import ValidationError

from app.modules.saha.schemas import OlcumPaketi

# Sabit ad alanı: (cihaz_kod, makine_kod, zaman) → kararlı olcum_id (CSV idempotency).
_AD_ALANI = uuid.UUID("0a8c3f9e-4b1d-4c2a-9f6e-7d5b2c1a0e9f")


class CsvGecersiz(Exception):
    """CSV biçimi/başlığı/satırı geçersiz."""


def csv_satirlari_coz(metin: str, *, cihaz_kod: str) -> list[OlcumPaketi]:
    okuyucu = csv.DictReader(io.StringIO(metin))
    if okuyucu.fieldnames is None or "makine_kod" not in okuyucu.fieldnames:
        raise CsvGecersiz("CSV başlığı eksik veya 'makine_kod' kolonu yok")
    paketler: list[OlcumPaketi] = []
    for i, satir in enumerate(okuyucu, start=2):  # 1 = başlık
        ham = dict(satir)
        if not ham.get("olcum_id"):
            cekirdek = f"{cihaz_kod}|{ham.get('makine_kod')}|{ham.get('zaman')}"
            ham["olcum_id"] = str(uuid.uuid5(_AD_ALANI, cekirdek))
        try:
            paketler.append(OlcumPaketi.model_validate(ham))
        except ValidationError as exc:
            raise CsvGecersiz(f"Satır {i} geçersiz: {exc.errors()[0]['msg']}") from exc
    if not paketler:
        raise CsvGecersiz("CSV boş")
    return paketler
