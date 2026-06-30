"""saha: saha_cihazlar + saha_alinan_olcum (Edge & Ingestion)

Revision ID: f3a9c1d72b84
Revises: c5a2f1b8e34d
Create Date: 2026-06-30 12:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) public + her aktif tenant şemasında çalışır.
Hypertable yoktur (düşük hacim + idempotency defteri normal tablo olmak zorunda).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'f3a9c1d72b84'
down_revision: str | None = 'c5a2f1b8e34d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'saha_cihazlar',
        sa.Column('kod', sa.String(length=50), nullable=False),
        sa.Column('ad', sa.String(length=200), nullable=False),
        sa.Column('protokol', sa.String(length=20), nullable=False),
        sa.Column('aktif', sa.Boolean(), nullable=False),
        sa.Column('son_gorulme', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('guncelleme_tarihi', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_saha_cihazlar')),
    )
    op.create_index(op.f('ix_saha_cihazlar_kod'), 'saha_cihazlar', ['kod'], unique=True)

    op.create_table(
        'saha_alinan_olcum',
        sa.Column('olcum_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('makine_id', sa.BigInteger(), nullable=False),
        sa.Column('alinma_zamani', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('olcum_id', name=op.f('pk_saha_alinan_olcum')),
    )


def downgrade() -> None:
    op.drop_table('saha_alinan_olcum')
    op.drop_index(op.f('ix_saha_cihazlar_kod'), table_name='saha_cihazlar')
    op.drop_table('saha_cihazlar')
