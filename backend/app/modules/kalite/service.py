"""Kalite iş kuralları — oto kod üretimi + CAPA durum geçişi (durum geçişi Task 4'te eklenir)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def kalite_kontrol_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def kalite_kontrol_kalici_kod(kontrol_id: int) -> str:
    """İnsan-okur kalite kontrol numarası: ``KK-{yıl}-{id:06d}``."""
    return f"KK-{datetime.now(UTC).year}-{kontrol_id:06d}"


def uygunsuzluk_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def uygunsuzluk_kalici_kod(uygunsuzluk_id: int) -> str:
    """İnsan-okur uygunsuzluk numarası: ``UY-{yıl}-{id:06d}``."""
    return f"UY-{datetime.now(UTC).year}-{uygunsuzluk_id:06d}"
