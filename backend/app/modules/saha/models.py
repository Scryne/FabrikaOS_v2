"""Saha modülü modelleri (tenant şeması).

- ``Cihaz`` — saha gateway kaydı (bir gateway N makine köprüleyebilir; makineye sabit
  FK yoktur, ölçüm ``makine_kod`` taşır).
- ``AlinanOlcum`` — idempotency defteri: işlenen ``olcum_id``'ler. Store-and-forward
  replay'inde çift-saymayı önler (``ON CONFLICT DO NOTHING``). Hypertable değildir.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

# Desteklenen saha protokolleri (MVP: simülasyon; opcua/modbus iskelet).
PROTOKOLLER = frozenset({"simulasyon", "opcua", "modbus"})


class Cihaz(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Saha gateway / veri kaynağı cihazı."""

    __tablename__ = "saha_cihazlar"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    protokol: Mapped[str] = mapped_column(String(20), default="simulasyon", nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    son_gorulme: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AlinanOlcum(TenantBase):
    """İşlenmiş ölçüm kimliği (idempotency defteri)."""

    __tablename__ = "saha_alinan_olcum"

    olcum_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    makine_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    alinma_zamani: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
