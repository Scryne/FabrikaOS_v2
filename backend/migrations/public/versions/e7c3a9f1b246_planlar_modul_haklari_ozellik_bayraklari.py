"""planlar + modul_haklari + ozellik_bayraklari (S16 / ADR-0018)

Revision ID: e7c3a9f1b246
Revises: d6dbf05143e2
Create Date: 2026-07-09

Plan seed'i migration içinde STATİK literaldir (migration app kodu import etmez);
kaynak gerçeği ``app/control_plane/moduller.py``'deki ``PLAN_KATALOGU``'dur ve
provizyonlama her koşuda upsert ile eşitler. FK (abonelik.plan_kodu -> planlar.kod)
seed'den SONRA eklenir — mevcut abonelikler ``deneme`` plan koduyla durur.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "e7c3a9f1b246"
down_revision: str | None = "d6dbf05143e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TUM_MODULLER = [
    "uretim",
    "saha",
    "isemri",
    "bakim",
    "stok",
    "kalite",
    "enerji",
    "isg",
    "ik",
    "crm",
    "sozlesme",
    "talep",
    "dys",
    "duyuru",
    "ai",
    "analitik",
    "rapor",
]
_TUM_OZELLIKLER = ["mobil-api", "webhook-onizleme"]
_TEMEL = ["uretim", "isemri", "bakim", "stok"]
_PROFESYONEL = _TEMEL + [
    "saha",
    "kalite",
    "enerji",
    "isg",
    "ik",
    "crm",
    "sozlesme",
    "talep",
    "dys",
    "duyuru",
]

_PLANLAR = [
    {"kod": "deneme", "ad": "Deneme", "koltuk_limiti": 5, "moduller": _TUM_MODULLER, "ozellikler": _TUM_OZELLIKLER},
    {"kod": "temel", "ad": "Temel", "koltuk_limiti": 10, "moduller": _TEMEL, "ozellikler": []},
    {"kod": "profesyonel", "ad": "Profesyonel", "koltuk_limiti": 50, "moduller": _PROFESYONEL, "ozellikler": []},
    {"kod": "kurumsal", "ad": "Kurumsal", "koltuk_limiti": None, "moduller": _TUM_MODULLER, "ozellikler": _TUM_OZELLIKLER},
]


def upgrade() -> None:
    planlar = op.create_table(
        "planlar",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("ad", sa.String(length=100), nullable=False),
        sa.Column("koltuk_limiti", sa.Integer(), nullable=True),
        sa.Column("moduller", JSONB(), nullable=False),
        sa.Column("ozellikler", JSONB(), nullable=False),
        sa.Column("aktif", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_planlar")),
        schema="public",
    )
    op.create_index(op.f("ix_public_planlar_kod"), "planlar", ["kod"], unique=True, schema="public")

    op.create_table(
        "modul_haklari",
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("modul_kodu", sa.String(length=50), nullable=False),
        sa.Column("acik", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenant.id"],
            name=op.f("fk_modul_haklari_tenant_id_tenant"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_modul_haklari")),
        sa.UniqueConstraint("tenant_id", "modul_kodu", name=op.f("uq_modul_haklari_tenant_id")),
        schema="public",
    )
    op.create_index(
        op.f("ix_public_modul_haklari_tenant_id"), "modul_haklari", ["tenant_id"], schema="public"
    )

    op.create_table(
        "ozellik_bayraklari",
        sa.Column("tenant_id", sa.BigInteger(), nullable=False),
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("acik", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["public.tenant.id"],
            name=op.f("fk_ozellik_bayraklari_tenant_id_tenant"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ozellik_bayraklari")),
        sa.UniqueConstraint("tenant_id", "kod", name=op.f("uq_ozellik_bayraklari_tenant_id")),
        schema="public",
    )
    op.create_index(
        op.f("ix_public_ozellik_bayraklari_tenant_id"),
        "ozellik_bayraklari",
        ["tenant_id"],
        schema="public",
    )

    # Plan kataloğu seed'i (statik) — FK'den ÖNCE gelmeli.
    op.bulk_insert(planlar, [{**p, "aktif": True} for p in _PLANLAR])

    op.create_foreign_key(
        op.f("fk_abonelik_plan_kodu_planlar"),
        "abonelik",
        "planlar",
        ["plan_kodu"],
        ["kod"],
        source_schema="public",
        referent_schema="public",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_abonelik_plan_kodu_planlar"), "abonelik", schema="public", type_="foreignkey"
    )
    op.drop_index(
        op.f("ix_public_ozellik_bayraklari_tenant_id"),
        table_name="ozellik_bayraklari",
        schema="public",
    )
    op.drop_table("ozellik_bayraklari", schema="public")
    op.drop_index(
        op.f("ix_public_modul_haklari_tenant_id"), table_name="modul_haklari", schema="public"
    )
    op.drop_table("modul_haklari", schema="public")
    op.drop_index(op.f("ix_public_planlar_kod"), table_name="planlar", schema="public")
    op.drop_table("planlar", schema="public")
