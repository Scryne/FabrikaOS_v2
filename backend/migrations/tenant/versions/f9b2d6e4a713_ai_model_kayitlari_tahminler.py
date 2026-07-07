"""ai: model_kayitlari (sürümlü model kayıt defteri) + tahminler (çıkarım geçmişi)

Revision ID: f9b2d6e4a713
Revises: e1f4a2c3b567
Create Date: 2026-07-07 10:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) public + her aktif tenant şemasında çalışır.
Hypertable/continuous aggregate yok. ``model_kayitlari`` önce oluşur (``tahminler`` FK verir).
Model artefaktının kendisi DB'de değil nesne deposundadır (``nesne_anahtari``).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "f9b2d6e4a713"
down_revision: str | None = "e1f4a2c3b567"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- AI: model_kayitlari (tahminler referans verir → önce) ---
    op.create_table(
        "model_kayitlari",
        sa.Column("tur", sa.String(length=30), nullable=False),
        sa.Column("surum", sa.Integer(), nullable=False),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="egitiliyor"),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("nesne_anahtari", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("metrikler", JSONB(), nullable=True),
        sa.Column("veri_ozeti", JSONB(), nullable=True),
        sa.Column("hata", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("egitim_suresi_sn", sa.Float(), nullable=True),
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
            name=op.f("fk_model_kayitlari_olusturan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_kayitlari")),
        sa.UniqueConstraint("tur", "surum", name="uq_model_kayitlari_tur_surum"),
    )
    op.create_index(op.f("ix_model_kayitlari_tur"), "model_kayitlari", ["tur"], unique=False)
    op.create_index(op.f("ix_model_kayitlari_durum"), "model_kayitlari", ["durum"], unique=False)
    op.create_index(op.f("ix_model_kayitlari_aktif"), "model_kayitlari", ["aktif"], unique=False)
    op.create_index(
        op.f("ix_model_kayitlari_olusturan_kullanici_id"),
        "model_kayitlari",
        ["olusturan_kullanici_id"],
        unique=False,
    )

    # --- AI: tahminler (çıkarım geçmişi) ---
    op.create_table(
        "tahminler",
        sa.Column("tur", sa.String(length=30), nullable=False),
        sa.Column("model_id", sa.BigInteger(), nullable=False),
        sa.Column("cikti", JSONB(), nullable=False),
        sa.Column("veri_ozeti", JSONB(), nullable=True),
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
            ["model_id"],
            ["model_kayitlari.id"],
            name=op.f("fk_tahminler_model_id_model_kayitlari"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["olusturan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_tahminler_olusturan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tahminler")),
    )
    op.create_index(op.f("ix_tahminler_tur"), "tahminler", ["tur"], unique=False)
    op.create_index(op.f("ix_tahminler_model_id"), "tahminler", ["model_id"], unique=False)
    op.create_index(
        op.f("ix_tahminler_olusturan_kullanici_id"),
        "tahminler",
        ["olusturan_kullanici_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_tahminler_olusturan_kullanici_id"), table_name="tahminler")
    op.drop_index(op.f("ix_tahminler_model_id"), table_name="tahminler")
    op.drop_index(op.f("ix_tahminler_tur"), table_name="tahminler")
    op.drop_table("tahminler")

    op.drop_index(op.f("ix_model_kayitlari_olusturan_kullanici_id"), table_name="model_kayitlari")
    op.drop_index(op.f("ix_model_kayitlari_aktif"), table_name="model_kayitlari")
    op.drop_index(op.f("ix_model_kayitlari_durum"), table_name="model_kayitlari")
    op.drop_index(op.f("ix_model_kayitlari_tur"), table_name="model_kayitlari")
    op.drop_table("model_kayitlari")
