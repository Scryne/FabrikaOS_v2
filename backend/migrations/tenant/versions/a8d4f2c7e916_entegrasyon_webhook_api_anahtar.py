"""entegrasyon: webhook_abonelikleri + webhook_teslimatlari + api_anahtarlari + kullanici.firma_id

Revision ID: a8d4f2c7e916
Revises: c9e6f2a8d135
Create Date: 2026-07-10 18:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) her aktif tenant şemasında çalışır.
Hypertable yok. ``kullanici.firma_id`` dış portal (S18) firma bağlantısıdır;
``webhook_teslimatlari.sonraki_deneme_tarihi`` vade taraması için indekslidir.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "a8d4f2c7e916"
down_revision: str | None = "c9e6f2a8d135"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _zaman_damgalari() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    # --- webhook_abonelikleri ---
    op.create_table(
        "webhook_abonelikleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ad", sa.String(length=120), nullable=False),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("gizli_anahtar", sa.String(length=120), nullable=False),
        sa.Column("olay_turleri", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_zaman_damgalari(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webhook_abonelikleri")),
    )

    # --- webhook_teslimatlari ---
    op.create_table(
        "webhook_teslimatlari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("dis_anahtar", UUID(as_uuid=True), nullable=False),
        sa.Column("abonelik_id", sa.BigInteger(), nullable=False),
        sa.Column("olay_id", sa.BigInteger(), nullable=False),
        sa.Column("olay_turu", sa.String(length=80), nullable=False),
        sa.Column("govde", JSONB(), nullable=False),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="beklemede"),
        sa.Column("deneme_sayisi", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "sonraki_deneme_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("son_deneme_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("yanit_kodu", sa.Integer(), nullable=True),
        sa.Column("yanit_ozeti", sa.String(length=500), nullable=False, server_default=""),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["abonelik_id"],
            ["webhook_abonelikleri.id"],
            name=op.f("fk_webhook_teslimatlari_abonelik_id_webhook_abonelikleri"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["olay_id"],
            ["giden_olaylar.id"],
            name=op.f("fk_webhook_teslimatlari_olay_id_giden_olaylar"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_webhook_teslimatlari")),
    )
    op.create_index(
        op.f("ix_webhook_teslimatlari_dis_anahtar"),
        "webhook_teslimatlari",
        ["dis_anahtar"],
        unique=True,
    )
    op.create_index(
        op.f("ix_webhook_teslimatlari_abonelik_id"), "webhook_teslimatlari", ["abonelik_id"]
    )
    op.create_index(op.f("ix_webhook_teslimatlari_olay_id"), "webhook_teslimatlari", ["olay_id"])
    op.create_index(
        op.f("ix_webhook_teslimatlari_olay_turu"), "webhook_teslimatlari", ["olay_turu"]
    )
    op.create_index(op.f("ix_webhook_teslimatlari_durum"), "webhook_teslimatlari", ["durum"])
    op.create_index(
        op.f("ix_webhook_teslimatlari_sonraki_deneme_tarihi"),
        "webhook_teslimatlari",
        ["sonraki_deneme_tarihi"],
    )

    # --- api_anahtarlari ---
    op.create_table(
        "api_anahtarlari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ad", sa.String(length=120), nullable=False),
        sa.Column("onek", sa.String(length=20), nullable=False),
        sa.Column("anahtar_ozet", sa.String(length=64), nullable=False),
        sa.Column("izinler", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("gecerlilik_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("son_kullanim_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("olusturan_kullanici_id", sa.BigInteger(), nullable=True),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["olusturan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_api_anahtarlari_olusturan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_api_anahtarlari")),
    )
    op.create_index(op.f("ix_api_anahtarlari_onek"), "api_anahtarlari", ["onek"])
    op.create_index(
        op.f("ix_api_anahtarlari_anahtar_ozet"), "api_anahtarlari", ["anahtar_ozet"], unique=True
    )
    op.create_index(
        op.f("ix_api_anahtarlari_olusturan_kullanici_id"),
        "api_anahtarlari",
        ["olusturan_kullanici_id"],
    )

    # --- kullanici.firma_id (dış portal bağlantısı) ---
    op.add_column("kullanici", sa.Column("firma_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_kullanici_firma_id_firmalar"),
        "kullanici",
        "firmalar",
        ["firma_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_kullanici_firma_id"), "kullanici", ["firma_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_kullanici_firma_id"), table_name="kullanici")
    op.drop_constraint(op.f("fk_kullanici_firma_id_firmalar"), "kullanici", type_="foreignkey")
    op.drop_column("kullanici", "firma_id")

    op.drop_index(op.f("ix_api_anahtarlari_olusturan_kullanici_id"), table_name="api_anahtarlari")
    op.drop_index(op.f("ix_api_anahtarlari_anahtar_ozet"), table_name="api_anahtarlari")
    op.drop_index(op.f("ix_api_anahtarlari_onek"), table_name="api_anahtarlari")
    op.drop_table("api_anahtarlari")

    op.drop_index(
        op.f("ix_webhook_teslimatlari_sonraki_deneme_tarihi"), table_name="webhook_teslimatlari"
    )
    op.drop_index(op.f("ix_webhook_teslimatlari_durum"), table_name="webhook_teslimatlari")
    op.drop_index(op.f("ix_webhook_teslimatlari_olay_turu"), table_name="webhook_teslimatlari")
    op.drop_index(op.f("ix_webhook_teslimatlari_olay_id"), table_name="webhook_teslimatlari")
    op.drop_index(op.f("ix_webhook_teslimatlari_abonelik_id"), table_name="webhook_teslimatlari")
    op.drop_index(op.f("ix_webhook_teslimatlari_dis_anahtar"), table_name="webhook_teslimatlari")
    op.drop_table("webhook_teslimatlari")

    op.drop_table("webhook_abonelikleri")
