"""Duyuru iş kuralları — oto kod (insan-okur numara)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def duyuru_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def duyuru_kalici_kod(duyuru_id: int) -> str:
    """İnsan-okur duyuru numarası: ``DUY-{yıl}-{id:06d}``."""
    return f"DUY-{datetime.now(UTC).year}-{duyuru_id:06d}"
