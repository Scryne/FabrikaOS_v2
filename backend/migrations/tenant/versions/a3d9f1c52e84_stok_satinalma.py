"""stok: malzemeler + stok_hareketleri + satinalma_talepleri + kalemler (Stok & Satınalma)

Revision ID: a3d9f1c52e84
Revises: f3a9c1d72b84
Create Date: 2026-06-30 14:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) public + her aktif tenant şemasında çalışır.
Hypertable yoktur (ilişkisel, düşük hacim). FK sırası: malzemeler önce, kalemler en son.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a3d9f1c52e84"
down_revision: str | None = "f3a9c1d72b84"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "malzemeler",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("birim", sa.String(length=20), nullable=False),
        sa.Column("kategori", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("mevcut_miktar", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("min_stok", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("max_stok", sa.Numeric(18, 3), nullable=True),
        sa.Column("kritik_stok", sa.Numeric(18, 3), nullable=False, server_default="0"),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.true()),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_malzemeler")),
    )
    op.create_index(op.f("ix_malzemeler_kod"), "malzemeler", ["kod"], unique=True)

    op.create_table(
        "stok_hareketleri",
        sa.Column("malzeme_id", sa.BigInteger(), nullable=False),
        sa.Column("tur", sa.String(length=10), nullable=False),
        sa.Column("miktar", sa.Numeric(18, 3), nullable=False),
        sa.Column("bakiye_sonrasi", sa.Numeric(18, 3), nullable=False),
        sa.Column("aciklama", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("kaynak", sa.String(length=50), nullable=True),
        sa.Column("olusturan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("idempotency_anahtari", sa.String(length=64), nullable=True),
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
            ["malzeme_id"],
            ["malzemeler.id"],
            name=op.f("fk_stok_hareketleri_malzeme_id_malzemeler"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["olusturan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_stok_hareketleri_olusturan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stok_hareketleri")),
    )
    op.create_index(
        op.f("ix_stok_hareketleri_malzeme_id"), "stok_hareketleri", ["malzeme_id"], unique=False
    )
    op.create_index(
        op.f("ix_stok_hareketleri_olusturan_kullanici_id"),
        "stok_hareketleri",
        ["olusturan_kullanici_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_stok_hareketleri_idempotency_anahtari"),
        "stok_hareketleri",
        ["idempotency_anahtari"],
        unique=True,
    )

    op.create_table(
        "satinalma_talepleri",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("baslik", sa.String(length=200), nullable=False),
        sa.Column("aciklama", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="taslak"),
        sa.Column("para_birimi", sa.String(length=3), nullable=False, server_default="TRY"),
        sa.Column("talep_eden_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("onaylayan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("onay_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("red_nedeni", sa.String(length=500), nullable=True),
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
            ["talep_eden_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_satinalma_talepleri_talep_eden_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["onaylayan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_satinalma_talepleri_onaylayan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_satinalma_talepleri")),
    )
    op.create_index(op.f("ix_satinalma_talepleri_kod"), "satinalma_talepleri", ["kod"], unique=True)
    op.create_index(
        op.f("ix_satinalma_talepleri_durum"), "satinalma_talepleri", ["durum"], unique=False
    )
    op.create_index(
        op.f("ix_satinalma_talepleri_talep_eden_kullanici_id"),
        "satinalma_talepleri",
        ["talep_eden_kullanici_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_satinalma_talepleri_onaylayan_kullanici_id"),
        "satinalma_talepleri",
        ["onaylayan_kullanici_id"],
        unique=False,
    )

    op.create_table(
        "satinalma_talebi_kalemleri",
        sa.Column("talep_id", sa.BigInteger(), nullable=False),
        sa.Column("malzeme_id", sa.BigInteger(), nullable=False),
        sa.Column("miktar", sa.Numeric(18, 3), nullable=False),
        sa.Column("birim", sa.String(length=20), nullable=False),
        sa.Column("tahmini_birim_fiyat", sa.Numeric(18, 2), nullable=True),
        sa.Column("aciklama", sa.String(length=500), nullable=False, server_default=""),
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
            ["talep_id"],
            ["satinalma_talepleri.id"],
            name=op.f("fk_satinalma_talebi_kalemleri_talep_id_satinalma_talepleri"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["malzeme_id"],
            ["malzemeler.id"],
            name=op.f("fk_satinalma_talebi_kalemleri_malzeme_id_malzemeler"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_satinalma_talebi_kalemleri")),
    )
    op.create_index(
        op.f("ix_satinalma_talebi_kalemleri_talep_id"),
        "satinalma_talebi_kalemleri",
        ["talep_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_satinalma_talebi_kalemleri_malzeme_id"),
        "satinalma_talebi_kalemleri",
        ["malzeme_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("satinalma_talebi_kalemleri")
    op.drop_index(
        op.f("ix_satinalma_talepleri_onaylayan_kullanici_id"), table_name="satinalma_talepleri"
    )
    op.drop_index(
        op.f("ix_satinalma_talepleri_talep_eden_kullanici_id"), table_name="satinalma_talepleri"
    )
    op.drop_index(op.f("ix_satinalma_talepleri_durum"), table_name="satinalma_talepleri")
    op.drop_index(op.f("ix_satinalma_talepleri_kod"), table_name="satinalma_talepleri")
    op.drop_table("satinalma_talepleri")
    op.drop_index(op.f("ix_stok_hareketleri_idempotency_anahtari"), table_name="stok_hareketleri")
    op.drop_index(op.f("ix_stok_hareketleri_olusturan_kullanici_id"), table_name="stok_hareketleri")
    op.drop_index(op.f("ix_stok_hareketleri_malzeme_id"), table_name="stok_hareketleri")
    op.drop_table("stok_hareketleri")
    op.drop_index(op.f("ix_malzemeler_kod"), table_name="malzemeler")
    op.drop_table("malzemeler")
