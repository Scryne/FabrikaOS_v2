"""S32 ESG & sürdürülebilirlik: emisyon faktörleri (ADR-0051).

Revision ID: c3e5a7b9d1f4
Revises: b2d4f6a8c0e3
Create Date: 2026-11-01 16:00:00.000000

Tenant şemasında; fan-out döngüsünde her aktif tenant şemasında çalışır. Emisyonun kendisi
saklanmaz (enerji tüketiminden her istekte hesaplanır); yalnız tenant'ın faktörleri tutulur.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3e5a7b9d1f4"
down_revision: str | None = "b2d4f6a8c0e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "emisyon_faktorleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("enerji_turu", sa.String(20), nullable=False),
        sa.Column("birim", sa.String(20), nullable=False),
        sa.Column("deger", sa.Numeric(14, 6), nullable=False),
        sa.Column("kapsam", sa.String(10), nullable=False),
        sa.Column("gecerlilik", sa.Date(), nullable=False),
        sa.Column("kaynak", sa.String(300), nullable=False, server_default=""),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("enerji_turu", "birim", "gecerlilik", name="uq_emisyon_faktorleri_tur"),
        sa.CheckConstraint("deger >= 0", name="ck_emisyon_faktorleri_deger"),
        sa.CheckConstraint("kapsam IN ('kapsam1', 'kapsam2')", name="ck_emisyon_faktorleri_kapsam"),
    )


def downgrade() -> None:
    op.drop_table("emisyon_faktorleri")
