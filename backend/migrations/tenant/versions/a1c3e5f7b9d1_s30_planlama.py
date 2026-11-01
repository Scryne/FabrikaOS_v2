"""S30 üretim planlama: iş emri plan girdisi (ADR-0049).

Revision ID: a1c3e5f7b9d1
Revises: f8a0c2e4b6d8
Create Date: 2026-11-01 08:00:00.000000

Tenant şemasında; fan-out döngüsünde her aktif tenant şemasında çalışır. Çizelge saklanmaz;
yalnız iş emri başına elle süre ve elle sıra tutulur.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c3e5f7b9d1"
down_revision: str | None = "f8a0c2e4b6d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "is_emri_planlari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("is_emri_id", sa.BigInteger(), nullable=False),
        sa.Column("sure_dk", sa.Numeric(10, 1), nullable=True),
        sa.Column("elle_sira", sa.Integer(), nullable=True),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["is_emri_id"], ["is_emirleri.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("is_emri_id", name="uq_is_emri_planlari_is_emri_id"),
        sa.CheckConstraint("sure_dk IS NULL OR sure_dk > 0", name="ck_is_emri_planlari_sure"),
    )


def downgrade() -> None:
    op.drop_table("is_emri_planlari")
