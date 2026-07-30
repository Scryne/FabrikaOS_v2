"""S23 güvenlik & uyum: tenant.guvenlik_ayarlari JSONB (parola politikası + 2FA
zorunluluğu + IP izin listesi; ADR-0022). NULL = varsayılan davranış.

Revision ID: a9d2e6f4c318
Revises: f2a8c4d9e517
Create Date: 2026-07-15 18:00:00.000000

Public şemada bir kez çalışır (control-plane).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "a9d2e6f4c318"
down_revision: str | None = "f2a8c4d9e517"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tenant", sa.Column("guvenlik_ayarlari", JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("tenant", "guvenlik_ayarlari")
