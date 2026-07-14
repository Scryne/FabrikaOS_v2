"""bildirim: bildirimler + bildirim_tercihleri + bildirim_imleci; SLA hedef_tarih;
makine coğrafi koordinat; tedarikçi skoru bağlantı kolonları (S-VB / ADR-0021).

Revision ID: b3e7c5f9a284
Revises: a8d4f2c7e916
Create Date: 2026-07-14 10:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) her aktif tenant şemasında çalışır.
Hypertable yok. ``bildirimler.UNIQUE(kullanici_id, giden_olay_id)`` üretici idempotency
kısıtıdır (ikinci tarama çift bildirim üretmez). ``malzemeler.tedarikci_firma_id`` +
``kalite_kontrolleri.malzeme_id`` tedarikçi performans skorunun kalite bileşenini
mümkün kılar (S25 satınalma siparişi hazırlığı).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "b3e7c5f9a284"
down_revision: str | None = "a8d4f2c7e916"
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
    # --- bildirimler ---
    op.create_table(
        "bildirimler",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kullanici_id", sa.BigInteger(), nullable=False),
        sa.Column("giden_olay_id", sa.BigInteger(), nullable=True),
        sa.Column("olay_turu", sa.String(length=80), nullable=False),
        sa.Column("baslik", sa.String(length=200), nullable=False),
        sa.Column("govde", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("veri", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("onem", sa.String(length=20), nullable=False, server_default="bilgi"),
        sa.Column("okundu", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("okundu_tarihi", sa.DateTime(timezone=True), nullable=True),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_bildirimler_kullanici_id_kullanici"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["giden_olay_id"],
            ["giden_olaylar.id"],
            name=op.f("fk_bildirimler_giden_olay_id_giden_olaylar"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bildirimler")),
        # Üretici idempotency: aynı olay aynı kullanıcıya bir kez düşer
        # (giden_olay_id IS NULL sistem bildirimleri kısıta girmez — PG NULL semantiği).
        sa.UniqueConstraint(
            "kullanici_id", "giden_olay_id", name=op.f("uq_bildirimler_kullanici_id")
        ),
    )
    op.create_index(op.f("ix_bildirimler_kullanici_id"), "bildirimler", ["kullanici_id"])
    op.create_index(op.f("ix_bildirimler_giden_olay_id"), "bildirimler", ["giden_olay_id"])
    op.create_index(op.f("ix_bildirimler_olay_turu"), "bildirimler", ["olay_turu"])
    op.create_index(op.f("ix_bildirimler_okundu"), "bildirimler", ["okundu"])

    # --- bildirim_tercihleri ---
    op.create_table(
        "bildirim_tercihleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kullanici_id", sa.BigInteger(), nullable=False),
        sa.Column("olay_turu", sa.String(length=80), nullable=False),
        sa.Column("uygulama_ici", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("eposta", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_bildirim_tercihleri_kullanici_id_kullanici"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bildirim_tercihleri")),
        sa.UniqueConstraint(
            "kullanici_id", "olay_turu", name=op.f("uq_bildirim_tercihleri_kullanici_id")
        ),
    )
    op.create_index(
        op.f("ix_bildirim_tercihleri_kullanici_id"), "bildirim_tercihleri", ["kullanici_id"]
    )

    # --- bildirim_imleci (tek satırlık yüksek-su-işareti) ---
    op.create_table(
        "bildirim_imleci",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column(
            "son_islenen_olay_id", sa.BigInteger(), nullable=False, server_default=sa.text("0")
        ),
        *_zaman_damgalari(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bildirim_imleci")),
    )

    # --- SLA hedef tarihleri (boş = SLA takibi yok) ---
    op.add_column(
        "is_emirleri", sa.Column("hedef_tarih", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("talepler", sa.Column("hedef_tarih", sa.DateTime(timezone=True), nullable=True))

    # --- Coğrafi site haritası (koordinatsız makine SVG şemada kalır) ---
    op.add_column("makineler", sa.Column("enlem", sa.Float(), nullable=True))
    op.add_column("makineler", sa.Column("boylam", sa.Float(), nullable=True))

    # --- Tedarikçi skoru bağlantıları ---
    op.add_column("malzemeler", sa.Column("tedarikci_firma_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_malzemeler_tedarikci_firma_id_firmalar"),
        "malzemeler",
        "firmalar",
        ["tedarikci_firma_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_malzemeler_tedarikci_firma_id"), "malzemeler", ["tedarikci_firma_id"])

    op.add_column("kalite_kontrolleri", sa.Column("malzeme_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_kalite_kontrolleri_malzeme_id_malzemeler"),
        "kalite_kontrolleri",
        "malzemeler",
        ["malzeme_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_kalite_kontrolleri_malzeme_id"), "kalite_kontrolleri", ["malzeme_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_kalite_kontrolleri_malzeme_id"), table_name="kalite_kontrolleri")
    op.drop_constraint(
        op.f("fk_kalite_kontrolleri_malzeme_id_malzemeler"),
        "kalite_kontrolleri",
        type_="foreignkey",
    )
    op.drop_column("kalite_kontrolleri", "malzeme_id")

    op.drop_index(op.f("ix_malzemeler_tedarikci_firma_id"), table_name="malzemeler")
    op.drop_constraint(
        op.f("fk_malzemeler_tedarikci_firma_id_firmalar"), "malzemeler", type_="foreignkey"
    )
    op.drop_column("malzemeler", "tedarikci_firma_id")

    op.drop_column("makineler", "boylam")
    op.drop_column("makineler", "enlem")
    op.drop_column("talepler", "hedef_tarih")
    op.drop_column("is_emirleri", "hedef_tarih")

    op.drop_table("bildirim_imleci")
    op.drop_index(op.f("ix_bildirim_tercihleri_kullanici_id"), table_name="bildirim_tercihleri")
    op.drop_table("bildirim_tercihleri")
    op.drop_index(op.f("ix_bildirimler_okundu"), table_name="bildirimler")
    op.drop_index(op.f("ix_bildirimler_olay_turu"), table_name="bildirimler")
    op.drop_index(op.f("ix_bildirimler_giden_olay_id"), table_name="bildirimler")
    op.drop_index(op.f("ix_bildirimler_kullanici_id"), table_name="bildirimler")
    op.drop_table("bildirimler")
