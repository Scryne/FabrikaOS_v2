"""Planlama modeli (tenant şeması, S30 / ADR-0049).

``IsEmriPlani`` — bir iş emrinin planlama girdisi: elle süre (yoksa tahmin edilir) ve elle sıra
(yoksa EDD). Çizelgenin kendisi saklanmaz; her istekte vardiyalar ve açık iş emirlerinden yeniden
hesaplanır (tek doğruluk kaynağı iş emri + plan girdisidir, bayat çizelge olmaz).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin


class IsEmriPlani(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "is_emri_planlari"
    __table_args__ = (
        CheckConstraint("sure_dk IS NULL OR sure_dk > 0", name="ck_is_emri_planlari_sure"),
    )

    is_emri_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("is_emirleri.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    sure_dk: Mapped[Decimal | None] = mapped_column(Numeric(10, 1), nullable=True)
    elle_sira: Mapped[int | None] = mapped_column(Integer, nullable=True)
