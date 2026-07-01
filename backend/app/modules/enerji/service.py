"""Enerji iş kuralları — ölçüm yazımı (append-only)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.enerji.models import EnerjiTuketim


async def olcum_yaz(
    db: AsyncSession,
    *,
    makine_id: int | None,
    enerji_turu: str,
    tuketim: Decimal,
    birim: str,
    zaman: datetime | None,
) -> EnerjiTuketim:
    """Enerji ölçümünü hypertable'a yazar (append-only)."""
    olcum = EnerjiTuketim(
        zaman=zaman or datetime.now(UTC),
        makine_id=makine_id,
        enerji_turu=enerji_turu,
        tuketim=tuketim,
        birim=birim,
    )
    db.add(olcum)
    await db.flush()
    return olcum
