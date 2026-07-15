"""S24 MES derinleşmesi: vardiya + duruş + ürün/reçete (BOM) + izlenebilirlik (lot) +
bakım olgunluğu kolonları (ADR-0023).

Revision ID: c4a7f3e9b528
Revises: b3e7c5f9a284
Create Date: 2026-07-15 09:00:00.000000

Tenant şemasında; fan-out döngüsünde her aktif tenant şemasında çalışır. Hypertable yok.
``receteler.urun_id`` UNIQUE = ürün başına tek aktif reçete (MVP; sürümleme Faz 6+).
``is_emirleri.bakim_plani_id`` otomatik bakım iş emri bağlantısı + bir-kez dedup'ıdır.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4a7f3e9b528"
down_revision: str | None = "b3e7c5f9a284"
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
    # --- vardiyalar ---
    op.create_table(
        "vardiyalar",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ad", sa.String(length=50), nullable=False),
        sa.Column("baslangic_saat", sa.Time(), nullable=False),
        sa.Column("bitis_saat", sa.Time(), nullable=False),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_zaman_damgalari(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vardiyalar")),
        sa.UniqueConstraint("ad", name=op.f("uq_vardiyalar_ad")),
    )

    # --- durus_nedenleri + durus_kayitlari ---
    op.create_table(
        "durus_nedenleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ad", sa.String(length=100), nullable=False),
        sa.Column("sinif", sa.String(length=10), nullable=False, server_default="plansiz"),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_zaman_damgalari(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_durus_nedenleri")),
        sa.UniqueConstraint("ad", name=op.f("uq_durus_nedenleri_ad")),
    )
    op.create_table(
        "durus_kayitlari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("makine_id", sa.BigInteger(), nullable=False),
        sa.Column("neden_id", sa.BigInteger(), nullable=False),
        sa.Column("baslangic", sa.DateTime(timezone=True), nullable=False),
        sa.Column("bitis", sa.DateTime(timezone=True), nullable=False),
        sa.Column("aciklama", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("olusturan_kullanici_id", sa.BigInteger(), nullable=True),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["makine_id"],
            ["makineler.id"],
            name=op.f("fk_durus_kayitlari_makine_id_makineler"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["neden_id"],
            ["durus_nedenleri.id"],
            name=op.f("fk_durus_kayitlari_neden_id_durus_nedenleri"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["olusturan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_durus_kayitlari_olusturan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_durus_kayitlari")),
    )
    op.create_index(op.f("ix_durus_kayitlari_makine_id"), "durus_kayitlari", ["makine_id"])
    op.create_index(op.f("ix_durus_kayitlari_neden_id"), "durus_kayitlari", ["neden_id"])
    op.create_index(op.f("ix_durus_kayitlari_baslangic"), "durus_kayitlari", ["baslangic"])

    # --- urunler + receteler + recete_kalemleri ---
    op.create_table(
        "urunler",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("birim", sa.String(length=20), nullable=False, server_default="adet"),
        sa.Column("aciklama", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_zaman_damgalari(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_urunler")),
    )
    op.create_index(op.f("ix_urunler_kod"), "urunler", ["kod"], unique=True)

    op.create_table(
        "receteler",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("urun_id", sa.BigInteger(), nullable=False),
        sa.Column("ad", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["urun_id"],
            ["urunler.id"],
            name=op.f("fk_receteler_urun_id_urunler"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_receteler")),
        # Ürün başına tek reçete (MVP) — sürümleme Faz 6+.
        sa.UniqueConstraint("urun_id", name=op.f("uq_receteler_urun_id")),
    )

    op.create_table(
        "recete_kalemleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("recete_id", sa.BigInteger(), nullable=False),
        sa.Column("malzeme_id", sa.BigInteger(), nullable=False),
        sa.Column("miktar", sa.Numeric(18, 3), nullable=False),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["recete_id"],
            ["receteler.id"],
            name=op.f("fk_recete_kalemleri_recete_id_receteler"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["malzeme_id"],
            ["malzemeler.id"],
            name=op.f("fk_recete_kalemleri_malzeme_id_malzemeler"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recete_kalemleri")),
        sa.UniqueConstraint("recete_id", "malzeme_id", name=op.f("uq_recete_kalemleri_recete_id")),
    )
    op.create_index(op.f("ix_recete_kalemleri_recete_id"), "recete_kalemleri", ["recete_id"])
    op.create_index(op.f("ix_recete_kalemleri_malzeme_id"), "recete_kalemleri", ["malzeme_id"])

    # --- is_emirleri: ürün/BOM + lot + bakım planı bağlantısı ---
    op.add_column("is_emirleri", sa.Column("urun_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_is_emirleri_urun_id_urunler"),
        "is_emirleri",
        "urunler",
        ["urun_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_is_emirleri_urun_id"), "is_emirleri", ["urun_id"])
    op.add_column("is_emirleri", sa.Column("miktar", sa.Numeric(18, 3), nullable=True))
    op.add_column("is_emirleri", sa.Column("lot_no", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_is_emirleri_lot_no"), "is_emirleri", ["lot_no"])
    op.add_column("is_emirleri", sa.Column("bakim_plani_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_is_emirleri_bakim_plani_id_bakim_planlari"),
        "is_emirleri",
        "bakim_planlari",
        ["bakim_plani_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_is_emirleri_bakim_plani_id"), "is_emirleri", ["bakim_plani_id"])
    op.add_column("is_emirleri", sa.Column("ariza_kaydi_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        op.f("fk_is_emirleri_ariza_kaydi_id_ariza_kayitlari"),
        "is_emirleri",
        "ariza_kayitlari",
        ["ariza_kaydi_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(op.f("ix_is_emirleri_ariza_kaydi_id"), "is_emirleri", ["ariza_kaydi_id"])

    # --- uretim_verileri: lot izlenebilirliği ---
    op.add_column("uretim_verileri", sa.Column("lot_no", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_uretim_verileri_lot_no"), "uretim_verileri", ["lot_no"])

    # --- bakım: yedek parça = malzeme ilişkisi ---
    op.add_column(
        "bakim_planlari", sa.Column("yedek_parca_malzeme_id", sa.BigInteger(), nullable=True)
    )
    op.create_foreign_key(
        op.f("fk_bakim_planlari_yedek_parca_malzeme_id_malzemeler"),
        "bakim_planlari",
        "malzemeler",
        ["yedek_parca_malzeme_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("fk_bakim_planlari_yedek_parca_malzeme_id_malzemeler"),
        "bakim_planlari",
        type_="foreignkey",
    )
    op.drop_column("bakim_planlari", "yedek_parca_malzeme_id")

    op.drop_index(op.f("ix_uretim_verileri_lot_no"), table_name="uretim_verileri")
    op.drop_column("uretim_verileri", "lot_no")

    op.drop_index(op.f("ix_is_emirleri_ariza_kaydi_id"), table_name="is_emirleri")
    op.drop_constraint(
        op.f("fk_is_emirleri_ariza_kaydi_id_ariza_kayitlari"), "is_emirleri", type_="foreignkey"
    )
    op.drop_column("is_emirleri", "ariza_kaydi_id")
    op.drop_index(op.f("ix_is_emirleri_bakim_plani_id"), table_name="is_emirleri")
    op.drop_constraint(
        op.f("fk_is_emirleri_bakim_plani_id_bakim_planlari"), "is_emirleri", type_="foreignkey"
    )
    op.drop_column("is_emirleri", "bakim_plani_id")
    op.drop_index(op.f("ix_is_emirleri_lot_no"), table_name="is_emirleri")
    op.drop_column("is_emirleri", "lot_no")
    op.drop_column("is_emirleri", "miktar")
    op.drop_index(op.f("ix_is_emirleri_urun_id"), table_name="is_emirleri")
    op.drop_constraint(op.f("fk_is_emirleri_urun_id_urunler"), "is_emirleri", type_="foreignkey")
    op.drop_column("is_emirleri", "urun_id")

    op.drop_index(op.f("ix_recete_kalemleri_malzeme_id"), table_name="recete_kalemleri")
    op.drop_index(op.f("ix_recete_kalemleri_recete_id"), table_name="recete_kalemleri")
    op.drop_table("recete_kalemleri")
    op.drop_table("receteler")
    op.drop_index(op.f("ix_urunler_kod"), table_name="urunler")
    op.drop_table("urunler")

    op.drop_index(op.f("ix_durus_kayitlari_baslangic"), table_name="durus_kayitlari")
    op.drop_index(op.f("ix_durus_kayitlari_neden_id"), table_name="durus_kayitlari")
    op.drop_index(op.f("ix_durus_kayitlari_makine_id"), table_name="durus_kayitlari")
    op.drop_table("durus_kayitlari")
    op.drop_table("durus_nedenleri")

    op.drop_table("vardiyalar")
