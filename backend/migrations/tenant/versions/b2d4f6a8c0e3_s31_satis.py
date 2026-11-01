"""S31 satış & sipariş → MRP (ADR-0050).

Revision ID: b2d4f6a8c0e3
Revises: a1c3e5f7b9d1
Create Date: 2026-11-01 14:00:00.000000

Tenant şemasında; fan-out döngüsünde her aktif tenant şemasında çalışır.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2d4f6a8c0e3"
down_revision: str | None = "a1c3e5f7b9d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _zaman() -> list[sa.Column]:
    return [
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "satis_siparisleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kod", sa.String(50), nullable=False),
        sa.Column("firma_id", sa.BigInteger(), nullable=False),
        sa.Column("talep_id", sa.BigInteger(), nullable=True),
        sa.Column("makine_id", sa.BigInteger(), nullable=True),
        sa.Column("durum", sa.String(20), nullable=False),
        sa.Column("teslim_tarihi", sa.Date(), nullable=False),
        sa.Column("para_birimi", sa.String(3), nullable=False),
        sa.Column("aciklama", sa.String(1000), nullable=False),
        sa.Column("olusturan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("onaylayan_kullanici_id", sa.BigInteger(), nullable=True),
        *_zaman(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["firma_id"], ["firmalar.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["talep_id"], ["talepler.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["makine_id"], ["makineler.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["olusturan_kullanici_id"], ["kullanici.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["onaylayan_kullanici_id"], ["kullanici.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("talep_id", name="uq_satis_siparisleri_talep_id"),
    )
    op.create_index("ix_satis_siparisleri_kod", "satis_siparisleri", ["kod"], unique=True)
    op.create_index("ix_satis_siparisleri_firma_id", "satis_siparisleri", ["firma_id"])
    op.create_index("ix_satis_siparisleri_durum", "satis_siparisleri", ["durum"])

    op.create_table(
        "satis_siparisi_kalemleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("siparis_id", sa.BigInteger(), nullable=False),
        sa.Column("sira", sa.Integer(), nullable=False),
        sa.Column("urun_id", sa.BigInteger(), nullable=False),
        sa.Column("miktar", sa.Numeric(18, 3), nullable=False),
        sa.Column("birim_fiyat", sa.Numeric(18, 4), nullable=True),
        *_zaman(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["siparis_id"], ["satis_siparisleri.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["urun_id"], ["urunler.id"], ondelete="RESTRICT"),
        sa.CheckConstraint("miktar > 0", name="ck_satis_siparisi_kalemleri_miktar"),
    )
    op.create_index("ix_satis_siparisi_kalemleri_siparis_id", "satis_siparisi_kalemleri", ["siparis_id"])

    op.create_table(
        "mrp_tetikleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("siparis_id", sa.BigInteger(), nullable=False),
        sa.Column("kaynak", sa.String(80), nullable=False),
        sa.Column("tur", sa.String(20), nullable=False),
        sa.Column("hedef_id", sa.BigInteger(), nullable=False),
        *_zaman(),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["siparis_id"], ["satis_siparisleri.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("kaynak", name="uq_mrp_tetikleri_kaynak"),
    )
    op.create_index("ix_mrp_tetikleri_siparis_id", "mrp_tetikleri", ["siparis_id"])


def downgrade() -> None:
    op.drop_table("mrp_tetikleri")
    op.drop_table("satis_siparisi_kalemleri")
    op.drop_table("satis_siparisleri")
