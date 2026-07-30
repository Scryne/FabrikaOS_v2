"""Rol–izin köken defteri: uzlaştırma tenant'ın kaldırdığı yetkiyi geri VERMESİN.

Revision ID: f4c8a2e6b791
Revises: e5b1c7d4a238
Create Date: 2026-07-31 09:20:00.000000

Uzlaştırma (``control_plane/uzlastirma.py``) "katalogda var, rolde yok" durumunu iki
sebebe ayırmalıdır: (a) yeni sprintin eklediği izin → eklenmeli; (b) tenant'ın bilinçli
olarak kaldırdığı izin → **dokunulmamalı**. Köken defteri olmadan ikisi ayırt edilemez ve
uzlaştırma denetlenemeyen bir yetki restorasyonu yapar.

**Backfill mantığı (kritik):** defter, mevcut ``rol_izin`` bağlarından doldurulur —
"bugünkü durum, bundan sonrası için başlangıç çizgisidir". Katalog kümesinden
doldurulsaydı, HENÜZ uzlaştırılmamış (sürüklenmiş) bir tenant'ta eksik izinler
"tohumlanmış" sayılır ve bir daha asla eklenmezdi; mevcut bağlardan doldurmak ise
tenant'ın o ana kadarki bilinçli kaldırmalarını korur.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4c8a2e6b791"
down_revision: str | None = "e5b1c7d4a238"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rol_izin_tohumu",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("rol_ad", sa.String(length=80), nullable=False),
        sa.Column("izin_kod", sa.String(length=80), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rol_izin_tohumu")),
        sa.UniqueConstraint("rol_ad", "izin_kod", name="uq_rol_izin_tohumu"),
    )
    op.create_index(op.f("ix_rol_izin_tohumu_rol_ad"), "rol_izin_tohumu", ["rol_ad"])

    # Backfill: bugünkü rol–izin bağları "katalogdan tohumlanmış" kabul edilir.
    op.execute(
        sa.text(
            "INSERT INTO rol_izin_tohumu (rol_ad, izin_kod) "
            "SELECT r.ad, i.kod FROM rol_izin ri "
            "JOIN rol r ON r.id = ri.rol_id "
            "JOIN izin i ON i.id = ri.izin_id "
            "ON CONFLICT (rol_ad, izin_kod) DO NOTHING"
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_rol_izin_tohumu_rol_ad"), table_name="rol_izin_tohumu")
    op.drop_table("rol_izin_tohumu")
