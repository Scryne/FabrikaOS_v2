"""İSG iş kuralları — oto kod üretimi (iş kazası + risk değerlendirme)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime


def kaza_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def kaza_kalici_kod(kaza_id: int) -> str:
    """İnsan-okur iş kazası numarası: ``KZ-{yıl}-{id:06d}``."""
    return f"KZ-{datetime.now(UTC).year}-{kaza_id:06d}"


def risk_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def risk_kalici_kod(risk_id: int) -> str:
    """İnsan-okur risk değerlendirme numarası: ``RD-{yıl}-{id:06d}``."""
    return f"RD-{datetime.now(UTC).year}-{risk_id:06d}"
