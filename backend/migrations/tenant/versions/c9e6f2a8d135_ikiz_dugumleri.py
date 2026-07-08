"""ikiz: ikiz_dugumleri (dijital ikiz tesis şeması yerleşimi)

Revision ID: c9e6f2a8d135
Revises: b4e8f2a6c159
Create Date: 2026-07-08 12:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) public + her aktif tenant şemasında çalışır.
Hypertable/continuous aggregate yok. Koordinatlar yüzde (0–100); bir makine şemada en
fazla bir kez yer alır (makine_id unique).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9e6f2a8d135"
down_revision: str | None = "b4e8f2a6c159"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ikiz_dugumleri",
        sa.Column("makine_id", sa.BigInteger(), nullable=False),
        sa.Column("x", sa.Float(), nullable=False),
        sa.Column("y", sa.Float(), nullable=False),
        sa.Column("bolge", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "olusturma_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "guncelleme_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["makine_id"],
            ["makineler.id"],
            name=op.f("fk_ikiz_dugumleri_makine_id_makineler"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ikiz_dugumleri")),
    )
    op.create_index(
        op.f("ix_ikiz_dugumleri_makine_id"), "ikiz_dugumleri", ["makine_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_ikiz_dugumleri_makine_id"), table_name="ikiz_dugumleri")
    op.drop_table("ikiz_dugumleri")
