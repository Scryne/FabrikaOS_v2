"""İK iş kuralları — oto kod (izin talebi) + KVKK maskeleme + izin gün hesabı.

``tc_maskele`` KVKK veri minimizasyonu gereği TC kimlik numarasını yanıtta gizler
(yalnız son 2 hane görünür). ``izin_gun_sayisi`` başlangıç/bitiş dâhil gün sayısını hesaplar.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime


def izin_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def izin_kalici_kod(izin_id: int) -> str:
    """İnsan-okur izin talebi numarası: ``IZ-{yıl}-{id:06d}``."""
    return f"IZ-{datetime.now(UTC).year}-{izin_id:06d}"


def tc_maskele(tc: str) -> str:
    """KVKK: TC kimlik numarasını maskeler; yalnız son 2 hane görünür (boşsa boş döner)."""
    if not tc:
        return ""
    if len(tc) <= 2:
        return "*" * len(tc)
    return "*" * (len(tc) - 2) + tc[-2:]


def izin_gun_sayisi(baslangic: date, bitis: date) -> int:
    """İzin gün sayısı (başlangıç ve bitiş dâhil); bitiş başlangıçtan önceyse 0."""
    fark = (bitis - baslangic).days + 1
    return max(fark, 0)
