"""kalite (denetim + CAPA) + enerji (hypertable + continuous aggregate)

Revision ID: b7e4c2f9a016
Revises: a3d9f1c52e84
Create Date: 2026-07-01 09:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) public + her aktif tenant şemasında çalışır.
Enerji hypertable + continuous aggregate. CAGG ``autocommit_block`` içinde oluşturulur
(TimescaleDB CAGG'i transaction bloğunda yaratamaz). search_path env'de ``SET`` (session)
ile ayarlandığından autocommit commit'inden sonra korunur → CAGG doğru tenant şemasında oluşur.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "b7e4c2f9a016"
down_revision: str | None = "a3d9f1c52e84"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "kalite_kontrolleri",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("makine_id", sa.BigInteger(), nullable=True),
        sa.Column("is_emri_id", sa.BigInteger(), nullable=True),
        sa.Column("kontrol_turu", sa.String(length=20), nullable=False, server_default="uretim"),
        sa.Column("sonuc", sa.String(length=20), nullable=False),
        sa.Column("olculen_deger", sa.Numeric(18, 3), nullable=True),
        sa.Column("alt_limit", sa.Numeric(18, 3), nullable=True),
        sa.Column("ust_limit", sa.Numeric(18, 3), nullable=True),
        sa.Column("numune_adedi", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("uygunsuz_adet", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("aciklama", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("kontrol_eden_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("zaman", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["makine_id"], ["makineler.id"], name=op.f("fk_kalite_kontrolleri_makine_id_makineler"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["is_emri_id"], ["is_emirleri.id"], name=op.f("fk_kalite_kontrolleri_is_emri_id_is_emirleri"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["kontrol_eden_kullanici_id"], ["kullanici.id"], name=op.f("fk_kalite_kontrolleri_kontrol_eden_kullanici_id_kullanici"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kalite_kontrolleri")),
    )
    op.create_index(op.f("ix_kalite_kontrolleri_kod"), "kalite_kontrolleri", ["kod"], unique=True)
    op.create_index(op.f("ix_kalite_kontrolleri_makine_id"), "kalite_kontrolleri", ["makine_id"], unique=False)
    op.create_index(op.f("ix_kalite_kontrolleri_is_emri_id"), "kalite_kontrolleri", ["is_emri_id"], unique=False)
    op.create_index(op.f("ix_kalite_kontrolleri_kontrol_eden_kullanici_id"), "kalite_kontrolleri", ["kontrol_eden_kullanici_id"], unique=False)

    op.create_table(
        "uygunsuzluklar",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("baslik", sa.String(length=200), nullable=False),
        sa.Column("aciklama", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("kaynak_kontrol_id", sa.BigInteger(), nullable=True),
        sa.Column("makine_id", sa.BigInteger(), nullable=True),
        sa.Column("onem", sa.String(length=20), nullable=False, server_default="orta"),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="acik"),
        sa.Column("kok_neden", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("acan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("sorumlu_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("dogrulama_notu", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("kapanis_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["kaynak_kontrol_id"], ["kalite_kontrolleri.id"], name=op.f("fk_uygunsuzluklar_kaynak_kontrol_id_kalite_kontrolleri"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["makine_id"], ["makineler.id"], name=op.f("fk_uygunsuzluklar_makine_id_makineler"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["acan_kullanici_id"], ["kullanici.id"], name=op.f("fk_uygunsuzluklar_acan_kullanici_id_kullanici"), ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["sorumlu_kullanici_id"], ["kullanici.id"], name=op.f("fk_uygunsuzluklar_sorumlu_kullanici_id_kullanici"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_uygunsuzluklar")),
    )
    op.create_index(op.f("ix_uygunsuzluklar_kod"), "uygunsuzluklar", ["kod"], unique=True)
    op.create_index(op.f("ix_uygunsuzluklar_kaynak_kontrol_id"), "uygunsuzluklar", ["kaynak_kontrol_id"], unique=False)
    op.create_index(op.f("ix_uygunsuzluklar_makine_id"), "uygunsuzluklar", ["makine_id"], unique=False)
    op.create_index(op.f("ix_uygunsuzluklar_onem"), "uygunsuzluklar", ["onem"], unique=False)
    op.create_index(op.f("ix_uygunsuzluklar_durum"), "uygunsuzluklar", ["durum"], unique=False)
    op.create_index(op.f("ix_uygunsuzluklar_acan_kullanici_id"), "uygunsuzluklar", ["acan_kullanici_id"], unique=False)
    op.create_index(op.f("ix_uygunsuzluklar_sorumlu_kullanici_id"), "uygunsuzluklar", ["sorumlu_kullanici_id"], unique=False)

    op.create_table(
        "capa_aksiyonlari",
        sa.Column("uygunsuzluk_id", sa.BigInteger(), nullable=False),
        sa.Column("tur", sa.String(length=20), nullable=False),
        sa.Column("aciklama", sa.String(length=1000), nullable=False),
        sa.Column("sorumlu_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("termin_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="planlandi"),
        sa.Column("tamamlanma_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["uygunsuzluk_id"], ["uygunsuzluklar.id"], name=op.f("fk_capa_aksiyonlari_uygunsuzluk_id_uygunsuzluklar"), ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sorumlu_kullanici_id"], ["kullanici.id"], name=op.f("fk_capa_aksiyonlari_sorumlu_kullanici_id_kullanici"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_capa_aksiyonlari")),
    )
    op.create_index(op.f("ix_capa_aksiyonlari_uygunsuzluk_id"), "capa_aksiyonlari", ["uygunsuzluk_id"], unique=False)
    op.create_index(op.f("ix_capa_aksiyonlari_sorumlu_kullanici_id"), "capa_aksiyonlari", ["sorumlu_kullanici_id"], unique=False)

    op.create_table(
        "enerji_tuketim",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=False), nullable=False),
        sa.Column("zaman", sa.DateTime(timezone=True), nullable=False),
        sa.Column("makine_id", sa.BigInteger(), nullable=True),
        sa.Column("enerji_turu", sa.String(length=20), nullable=False),
        sa.Column("tuketim", sa.Numeric(18, 3), nullable=False),
        sa.Column("birim", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["makine_id"], ["makineler.id"], name=op.f("fk_enerji_tuketim_makine_id_makineler"), ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("zaman", "id", name="pk_enerji_tuketim"),
    )
    op.create_index("ix_enerji_tuketim_makine_zaman", "enerji_tuketim", ["makine_id", "zaman"], unique=False)
    op.create_index("ix_enerji_tuketim_turu_zaman", "enerji_tuketim", ["enerji_turu", "zaman"], unique=False)

    # enerji_tuketim'i hypertable'a çevir (transaction içinde çalışır — uretim'de kanıtlı).
    op.execute("SELECT create_hypertable('enerji_tuketim', 'zaman', if_not_exists => TRUE)")

    # Continuous aggregate + refresh policy TRANSACTION DIŞINDA olmalı (TimescaleDB kısıtı).
    with op.get_context().autocommit_block():
        op.execute(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS enerji_tuketim_saatlik
            WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
            SELECT time_bucket('1 hour', zaman) AS kova,
                   makine_id,
                   enerji_turu,
                   sum(tuketim) AS toplam_tuketim,
                   count(*) AS olcum_adedi
            FROM enerji_tuketim
            GROUP BY kova, makine_id, enerji_turu
            WITH NO DATA
            """
        )
        op.execute(
            """
            SELECT add_continuous_aggregate_policy('enerji_tuketim_saatlik',
                start_offset => INTERVAL '3 days',
                end_offset => INTERVAL '1 hour',
                schedule_interval => INTERVAL '1 hour',
                if_not_exists => TRUE)
            """
        )


def downgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("DROP MATERIALIZED VIEW IF EXISTS enerji_tuketim_saatlik")
    op.drop_index("ix_enerji_tuketim_turu_zaman", table_name="enerji_tuketim")
    op.drop_index("ix_enerji_tuketim_makine_zaman", table_name="enerji_tuketim")
    op.drop_table("enerji_tuketim")
    op.drop_index(op.f("ix_capa_aksiyonlari_sorumlu_kullanici_id"), table_name="capa_aksiyonlari")
    op.drop_index(op.f("ix_capa_aksiyonlari_uygunsuzluk_id"), table_name="capa_aksiyonlari")
    op.drop_table("capa_aksiyonlari")
    op.drop_index(op.f("ix_uygunsuzluklar_sorumlu_kullanici_id"), table_name="uygunsuzluklar")
    op.drop_index(op.f("ix_uygunsuzluklar_acan_kullanici_id"), table_name="uygunsuzluklar")
    op.drop_index(op.f("ix_uygunsuzluklar_durum"), table_name="uygunsuzluklar")
    op.drop_index(op.f("ix_uygunsuzluklar_onem"), table_name="uygunsuzluklar")
    op.drop_index(op.f("ix_uygunsuzluklar_makine_id"), table_name="uygunsuzluklar")
    op.drop_index(op.f("ix_uygunsuzluklar_kaynak_kontrol_id"), table_name="uygunsuzluklar")
    op.drop_index(op.f("ix_uygunsuzluklar_kod"), table_name="uygunsuzluklar")
    op.drop_table("uygunsuzluklar")
    op.drop_index(op.f("ix_kalite_kontrolleri_kontrol_eden_kullanici_id"), table_name="kalite_kontrolleri")
    op.drop_index(op.f("ix_kalite_kontrolleri_is_emri_id"), table_name="kalite_kontrolleri")
    op.drop_index(op.f("ix_kalite_kontrolleri_makine_id"), table_name="kalite_kontrolleri")
    op.drop_index(op.f("ix_kalite_kontrolleri_kod"), table_name="kalite_kontrolleri")
    op.drop_table("kalite_kontrolleri")
