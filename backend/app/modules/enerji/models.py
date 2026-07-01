"""Enerji modülü modelleri (tenant şeması).

``EnerjiTuketim`` — TimescaleDB **hypertable** (yüksek hacimli zaman serisi); partition
kolonu ``zaman``, PK ``(zaman, id)`` (uretim ``UretimVerisi`` deseni). ``makine_id`` nullable
= tesis geneli tüketim. Continuous aggregate (``enerji_tuketim_saatlik``) migration'da kurulur.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import TenantBase


class EnerjiTuketim(TenantBase):
    """Enerji tüketim ölçümü (zaman serisi / hypertable)."""

    __tablename__ = "enerji_tuketim"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    zaman: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    makine_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="SET NULL"), nullable=True
    )
    enerji_turu: Mapped[str] = mapped_column(String(20), nullable=False)
    tuketim: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)
    birim: Mapped[str] = mapped_column(String(20), nullable=False)

    __table_args__ = (
        PrimaryKeyConstraint("zaman", "id", name="pk_enerji_tuketim"),
        Index("ix_enerji_tuketim_makine_zaman", "makine_id", "zaman"),
        Index("ix_enerji_tuketim_turu_zaman", "enerji_turu", "zaman"),
    )
