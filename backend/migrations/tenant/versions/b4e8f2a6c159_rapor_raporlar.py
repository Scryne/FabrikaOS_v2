"""rapor: raporlar (async üretilen rapor kayıtları)

Revision ID: b4e8f2a6c159
Revises: f9b2d6e4a713
Create Date: 2026-07-07 16:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) public + her aktif tenant şemasında çalışır.
Hypertable/continuous aggregate yok. Rapor dosyasının kendisi DB'de değil nesne
deposundadır (``nesne_anahtari``).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "b4e8f2a6c159"
down_revision: str | None = "f9b2d6e4a713"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "raporlar",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("tur", sa.String(length=30), nullable=False),
        sa.Column("bicim", sa.String(length=10), nullable=False),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="kuyrukta"),
        sa.Column("parametreler", JSONB(), nullable=True),
        sa.Column("nesne_anahtari", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("dosya_adi", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("icerik_tipi", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("boyut", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("satir_sayisi", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("hata", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("uretim_suresi_sn", sa.Float(), nullable=True),
        sa.Column("olusturan_kullanici_id", sa.BigInteger(), nullable=True),
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
            ["olusturan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_raporlar_olusturan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_raporlar")),
    )
    op.create_index(op.f("ix_raporlar_kod"), "raporlar", ["kod"], unique=True)
    op.create_index(op.f("ix_raporlar_tur"), "raporlar", ["tur"], unique=False)
    op.create_index(op.f("ix_raporlar_durum"), "raporlar", ["durum"], unique=False)
    op.create_index(
        op.f("ix_raporlar_olusturan_kullanici_id"),
        "raporlar",
        ["olusturan_kullanici_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_raporlar_olusturan_kullanici_id"), table_name="raporlar")
    op.drop_index(op.f("ix_raporlar_durum"), table_name="raporlar")
    op.drop_index(op.f("ix_raporlar_tur"), table_name="raporlar")
    op.drop_index(op.f("ix_raporlar_kod"), table_name="raporlar")
    op.drop_table("raporlar")
