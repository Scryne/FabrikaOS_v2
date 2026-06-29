"""Bakım modülü modelleri (tenant şeması).

- ``BakimPlani`` — makineye n–1 bağlı bakım planı (önleyici/kestirimci/periyodik). Bu sprintte
  yalnızca CRUD; plandan otomatik iş emri üretimi (zamanlayıcı) ileride ele alınacaktır.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

# Bakım planı türleri.
BAKIM_TIPLERI = frozenset({"onleyici", "kestirimci", "periyodik"})


class BakimPlani(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Makineye bağlı bakım planı."""

    __tablename__ = "bakim_planlari"

    makine_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    tip: Mapped[str] = mapped_column(String(20), default="onleyici", nullable=False)
    periyot_gun: Mapped[int | None] = mapped_column(Integer, nullable=True)
    son_bakim_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sonraki_bakim_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
