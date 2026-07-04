"""isg (is kazasi + risk degerlendirme) + ik (personel + izin/mesai/zimmet/sertifika)

Revision ID: d5c8e1f0a927
Revises: b7e4c2f9a016
Create Date: 2026-07-04 11:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) public + her aktif tenant şemasında çalışır.
Hypertable/continuous aggregate yok. Tablolar FK bağımlılığına göre sıralanır: ``personel``
önce oluşturulur (İSG kazası + tüm İK yardımcı tabloları ona referans verir).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d5c8e1f0a927"
down_revision: str | None = "b7e4c2f9a016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- İK: personel (diğer tablolar referans verir → önce) ---
    op.create_table(
        "personel",
        sa.Column("sicil_no", sa.String(length=50), nullable=False),
        sa.Column("ad", sa.String(length=100), nullable=False),
        sa.Column("soyad", sa.String(length=100), nullable=False),
        sa.Column("tc_kimlik_no", sa.String(length=11), nullable=False, server_default=""),
        sa.Column("dogum_tarihi", sa.Date(), nullable=True),
        sa.Column("telefon", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("eposta", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("departman", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("unvan", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("ise_giris_tarihi", sa.Date(), nullable=True),
        sa.Column("yillik_izin_hakki", sa.Integer(), nullable=False, server_default="14"),
        sa.Column("kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
            ["kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_personel_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_personel")),
    )
    op.create_index(op.f("ix_personel_sicil_no"), "personel", ["sicil_no"], unique=True)
    op.create_index(op.f("ix_personel_departman"), "personel", ["departman"], unique=False)
    op.create_index(op.f("ix_personel_kullanici_id"), "personel", ["kullanici_id"], unique=False)

    # --- İSG: is_kazalari ---
    op.create_table(
        "is_kazalari",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("tur", sa.String(length=20), nullable=False, server_default="kaza"),
        sa.Column(
            "olay_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("yer", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("aciklama", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("agirlik", sa.String(length=20), nullable=False, server_default="hafif"),
        sa.Column("kaybedilen_gun", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("yaralanma_turu", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("personel_id", sa.BigInteger(), nullable=True),
        sa.Column("makine_id", sa.BigInteger(), nullable=True),
        sa.Column("raporlayan_kullanici_id", sa.BigInteger(), nullable=True),
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
            ["personel_id"],
            ["personel.id"],
            name=op.f("fk_is_kazalari_personel_id_personel"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["makine_id"],
            ["makineler.id"],
            name=op.f("fk_is_kazalari_makine_id_makineler"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["raporlayan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_is_kazalari_raporlayan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_is_kazalari")),
    )
    op.create_index(op.f("ix_is_kazalari_kod"), "is_kazalari", ["kod"], unique=True)
    op.create_index(op.f("ix_is_kazalari_tur"), "is_kazalari", ["tur"], unique=False)
    op.create_index(op.f("ix_is_kazalari_agirlik"), "is_kazalari", ["agirlik"], unique=False)
    op.create_index(
        op.f("ix_is_kazalari_personel_id"), "is_kazalari", ["personel_id"], unique=False
    )
    op.create_index(op.f("ix_is_kazalari_makine_id"), "is_kazalari", ["makine_id"], unique=False)
    op.create_index(
        op.f("ix_is_kazalari_raporlayan_kullanici_id"),
        "is_kazalari",
        ["raporlayan_kullanici_id"],
        unique=False,
    )

    # --- İSG: risk_degerlendirmeleri ---
    op.create_table(
        "risk_degerlendirmeleri",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("baslik", sa.String(length=200), nullable=False),
        sa.Column("bolum", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("tehlike", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("olasilik", sa.Integer(), nullable=False),
        sa.Column("siddet", sa.Integer(), nullable=False),
        sa.Column("risk_skoru", sa.Integer(), nullable=False),
        sa.Column("risk_seviyesi", sa.String(length=20), nullable=False),
        sa.Column("onlem", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="acik"),
        sa.Column("sorumlu_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "degerlendirme_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("gecerlilik_tarihi", sa.Date(), nullable=True),
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
            ["sorumlu_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_risk_degerlendirmeleri_sorumlu_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_risk_degerlendirmeleri")),
    )
    op.create_index(
        op.f("ix_risk_degerlendirmeleri_kod"), "risk_degerlendirmeleri", ["kod"], unique=True
    )
    op.create_index(
        op.f("ix_risk_degerlendirmeleri_risk_seviyesi"),
        "risk_degerlendirmeleri",
        ["risk_seviyesi"],
        unique=False,
    )
    op.create_index(
        op.f("ix_risk_degerlendirmeleri_durum"),
        "risk_degerlendirmeleri",
        ["durum"],
        unique=False,
    )
    op.create_index(
        op.f("ix_risk_degerlendirmeleri_sorumlu_kullanici_id"),
        "risk_degerlendirmeleri",
        ["sorumlu_kullanici_id"],
        unique=False,
    )

    # --- İK: izin_talepleri ---
    op.create_table(
        "izin_talepleri",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("personel_id", sa.BigInteger(), nullable=False),
        sa.Column("izin_turu", sa.String(length=20), nullable=False, server_default="yillik"),
        sa.Column("baslangic_tarihi", sa.Date(), nullable=False),
        sa.Column("bitis_tarihi", sa.Date(), nullable=False),
        sa.Column("gun_sayisi", sa.Integer(), nullable=False),
        sa.Column("aciklama", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="taslak"),
        sa.Column("talep_eden_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("onaylayan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("onay_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("red_nedeni", sa.String(length=1000), nullable=False, server_default=""),
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
            ["personel_id"],
            ["personel.id"],
            name=op.f("fk_izin_talepleri_personel_id_personel"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["talep_eden_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_izin_talepleri_talep_eden_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["onaylayan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_izin_talepleri_onaylayan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_izin_talepleri")),
    )
    op.create_index(op.f("ix_izin_talepleri_kod"), "izin_talepleri", ["kod"], unique=True)
    op.create_index(
        op.f("ix_izin_talepleri_personel_id"), "izin_talepleri", ["personel_id"], unique=False
    )
    op.create_index(op.f("ix_izin_talepleri_durum"), "izin_talepleri", ["durum"], unique=False)
    op.create_index(
        op.f("ix_izin_talepleri_talep_eden_kullanici_id"),
        "izin_talepleri",
        ["talep_eden_kullanici_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_izin_talepleri_onaylayan_kullanici_id"),
        "izin_talepleri",
        ["onaylayan_kullanici_id"],
        unique=False,
    )

    # --- İK: fazla_mesailer ---
    op.create_table(
        "fazla_mesailer",
        sa.Column("personel_id", sa.BigInteger(), nullable=False),
        sa.Column("tarih", sa.Date(), nullable=False),
        sa.Column("saat", sa.Numeric(6, 2), nullable=False),
        sa.Column("aciklama", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("onayli", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
            ["personel_id"],
            ["personel.id"],
            name=op.f("fk_fazla_mesailer_personel_id_personel"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["olusturan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_fazla_mesailer_olusturan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fazla_mesailer")),
    )
    op.create_index(
        op.f("ix_fazla_mesailer_personel_id"), "fazla_mesailer", ["personel_id"], unique=False
    )
    op.create_index(
        op.f("ix_fazla_mesailer_olusturan_kullanici_id"),
        "fazla_mesailer",
        ["olusturan_kullanici_id"],
        unique=False,
    )

    # --- İK: zimmetler ---
    op.create_table(
        "zimmetler",
        sa.Column("personel_id", sa.BigInteger(), nullable=False),
        sa.Column("demirbas", sa.String(length=200), nullable=False),
        sa.Column("seri_no", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("zimmet_tarihi", sa.Date(), nullable=False),
        sa.Column("iade_tarihi", sa.Date(), nullable=True),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="zimmetli"),
        sa.Column("aciklama", sa.String(length=1000), nullable=False, server_default=""),
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
            ["personel_id"],
            ["personel.id"],
            name=op.f("fk_zimmetler_personel_id_personel"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_zimmetler")),
    )
    op.create_index(op.f("ix_zimmetler_personel_id"), "zimmetler", ["personel_id"], unique=False)
    op.create_index(op.f("ix_zimmetler_durum"), "zimmetler", ["durum"], unique=False)

    # --- İK: sertifikalar ---
    op.create_table(
        "sertifikalar",
        sa.Column("personel_id", sa.BigInteger(), nullable=False),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("kurum", sa.String(length=200), nullable=False, server_default=""),
        sa.Column("belge_no", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("alinma_tarihi", sa.Date(), nullable=False),
        sa.Column("gecerlilik_tarihi", sa.Date(), nullable=True),
        sa.Column("aciklama", sa.String(length=1000), nullable=False, server_default=""),
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
            ["personel_id"],
            ["personel.id"],
            name=op.f("fk_sertifikalar_personel_id_personel"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sertifikalar")),
    )
    op.create_index(
        op.f("ix_sertifikalar_personel_id"), "sertifikalar", ["personel_id"], unique=False
    )
    op.create_index(
        op.f("ix_sertifikalar_gecerlilik_tarihi"),
        "sertifikalar",
        ["gecerlilik_tarihi"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_sertifikalar_gecerlilik_tarihi"), table_name="sertifikalar")
    op.drop_index(op.f("ix_sertifikalar_personel_id"), table_name="sertifikalar")
    op.drop_table("sertifikalar")
    op.drop_index(op.f("ix_zimmetler_durum"), table_name="zimmetler")
    op.drop_index(op.f("ix_zimmetler_personel_id"), table_name="zimmetler")
    op.drop_table("zimmetler")
    op.drop_index(op.f("ix_fazla_mesailer_olusturan_kullanici_id"), table_name="fazla_mesailer")
    op.drop_index(op.f("ix_fazla_mesailer_personel_id"), table_name="fazla_mesailer")
    op.drop_table("fazla_mesailer")
    op.drop_index(op.f("ix_izin_talepleri_onaylayan_kullanici_id"), table_name="izin_talepleri")
    op.drop_index(op.f("ix_izin_talepleri_talep_eden_kullanici_id"), table_name="izin_talepleri")
    op.drop_index(op.f("ix_izin_talepleri_durum"), table_name="izin_talepleri")
    op.drop_index(op.f("ix_izin_talepleri_personel_id"), table_name="izin_talepleri")
    op.drop_index(op.f("ix_izin_talepleri_kod"), table_name="izin_talepleri")
    op.drop_table("izin_talepleri")
    op.drop_index(
        op.f("ix_risk_degerlendirmeleri_sorumlu_kullanici_id"),
        table_name="risk_degerlendirmeleri",
    )
    op.drop_index(op.f("ix_risk_degerlendirmeleri_durum"), table_name="risk_degerlendirmeleri")
    op.drop_index(
        op.f("ix_risk_degerlendirmeleri_risk_seviyesi"), table_name="risk_degerlendirmeleri"
    )
    op.drop_index(op.f("ix_risk_degerlendirmeleri_kod"), table_name="risk_degerlendirmeleri")
    op.drop_table("risk_degerlendirmeleri")
    op.drop_index(op.f("ix_is_kazalari_raporlayan_kullanici_id"), table_name="is_kazalari")
    op.drop_index(op.f("ix_is_kazalari_makine_id"), table_name="is_kazalari")
    op.drop_index(op.f("ix_is_kazalari_personel_id"), table_name="is_kazalari")
    op.drop_index(op.f("ix_is_kazalari_agirlik"), table_name="is_kazalari")
    op.drop_index(op.f("ix_is_kazalari_tur"), table_name="is_kazalari")
    op.drop_index(op.f("ix_is_kazalari_kod"), table_name="is_kazalari")
    op.drop_table("is_kazalari")
    op.drop_index(op.f("ix_personel_kullanici_id"), table_name="personel")
    op.drop_index(op.f("ix_personel_departman"), table_name="personel")
    op.drop_index(op.f("ix_personel_sicil_no"), table_name="personel")
    op.drop_table("personel")
