"""SPC → CAPA köprüsü: uygunsuzluğu kural ihlali taşıyan SPC alt grubuna bağlar.

Revision ID: e7a9c1d3f5b2
Revises: c3e5a7b9d1f4
Create Date: 2026-11-14

- ``uygunsuzluklar.kaynak_spc_alt_grup_id`` → ``spc_alt_gruplari.id`` (SET NULL), UNIQUE:
  ihlalli alt grup başına tek vaka (kaza → CAPA köprüsüyle aynı desen, ADR-0044).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7a9c1d3f5b2"
down_revision: str | None = "c3e5a7b9d1f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "uygunsuzluklar", sa.Column("kaynak_spc_alt_grup_id", sa.BigInteger(), nullable=True)
    )
    op.create_foreign_key(
        "fk_uygunsuzluklar_kaynak_spc_alt_grup_id",
        "uygunsuzluklar",
        "spc_alt_gruplari",
        ["kaynak_spc_alt_grup_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_uygunsuzluklar_kaynak_spc_alt_grup_id",
        "uygunsuzluklar",
        ["kaynak_spc_alt_grup_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_uygunsuzluklar_kaynak_spc_alt_grup_id", table_name="uygunsuzluklar")
    op.drop_constraint(
        "fk_uygunsuzluklar_kaynak_spc_alt_grup_id", "uygunsuzluklar", type_="foreignkey"
    )
    op.drop_column("uygunsuzluklar", "kaynak_spc_alt_grup_id")
