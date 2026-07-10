"""platform_yonetici + tenant_ihraclari + platform_denetim_izi (S17 / ADR-0019)

Revision ID: f2a8c4d9e517
Revises: e7c3a9f1b246
Create Date: 2026-07-10

Yalnız public (control-plane) ağacına dokunur — tenant fan-out YOK. İlk platform
yöneticisi seed EDİLMEZ; ``backend/scripts/platform_yonetici_olustur.py`` CLI ile
açılır (parola migration'a gömülmez).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "f2a8c4d9e517"
down_revision: str | None = "e7c3a9f1b246"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "platform_yonetici",
        sa.Column("eposta", sa.String(length=255), nullable=False),
        sa.Column("parola_ozet", sa.String(length=255), nullable=False),
        sa.Column("ad_soyad", sa.String(length=200), nullable=False),
        sa.Column("aktif", sa.Boolean(), nullable=False),
        sa.Column("son_giris_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_yonetici")),
        schema="public",
    )
    op.create_index(
        op.f("ix_public_platform_yonetici_eposta"),
        "platform_yonetici",
        ["eposta"],
        unique=True,
        schema="public",
    )

    op.create_table(
        "tenant_ihraclari",
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("slug", sa.String(length=63), nullable=False),
        sa.Column("durum", sa.String(length=20), nullable=False),
        sa.Column("nesne_anahtari", sa.String(length=500), nullable=True),
        sa.Column("boyut", sa.BigInteger(), nullable=True),
        sa.Column("tablo_sayisi", sa.Integer(), nullable=True),
        sa.Column("hata", sa.String(length=1000), nullable=True),
        sa.Column("olusturan_eposta", sa.String(length=255), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenant.id"],
            name=op.f("fk_tenant_ihraclari_tenant_id_tenant"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tenant_ihraclari")),
        schema="public",
    )
    op.create_index(
        op.f("ix_public_tenant_ihraclari_tenant_id"),
        "tenant_ihraclari",
        ["tenant_id"],
        schema="public",
    )

    op.create_table(
        "platform_denetim_izi",
        sa.Column("yonetici_id", sa.BigInteger(), nullable=True),
        sa.Column("yonetici_eposta", sa.String(length=255), nullable=True),
        sa.Column("eylem", sa.String(length=50), nullable=False),
        sa.Column("kaynak", sa.String(length=80), nullable=False),
        sa.Column("kaynak_id", sa.String(length=80), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("ip_adresi", sa.String(length=64), nullable=True),
        sa.Column("detay", JSONB(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_platform_denetim_izi")),
        schema="public",
    )
    op.create_index(
        op.f("ix_public_platform_denetim_izi_yonetici_id"),
        "platform_denetim_izi",
        ["yonetici_id"],
        schema="public",
    )
    op.create_index(
        op.f("ix_public_platform_denetim_izi_kaynak"),
        "platform_denetim_izi",
        ["kaynak"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_public_platform_denetim_izi_kaynak"),
        table_name="platform_denetim_izi",
        schema="public",
    )
    op.drop_index(
        op.f("ix_public_platform_denetim_izi_yonetici_id"),
        table_name="platform_denetim_izi",
        schema="public",
    )
    op.drop_table("platform_denetim_izi", schema="public")
    op.drop_index(
        op.f("ix_public_tenant_ihraclari_tenant_id"),
        table_name="tenant_ihraclari",
        schema="public",
    )
    op.drop_table("tenant_ihraclari", schema="public")
    op.drop_index(
        op.f("ix_public_platform_yonetici_eposta"),
        table_name="platform_yonetici",
        schema="public",
    )
    op.drop_table("platform_yonetici", schema="public")
