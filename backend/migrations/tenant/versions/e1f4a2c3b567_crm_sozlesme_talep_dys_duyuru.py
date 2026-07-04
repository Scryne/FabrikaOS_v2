"""crm (firma+ortak) + sozlesme + talep + dys (belge+surum) + duyuru

Revision ID: e1f4a2c3b567
Revises: d5c8e1f0a927
Create Date: 2026-07-04 15:00:00.000000

Tenant şemasında; fan-out döngüsünde (env.py) public + her aktif tenant şemasında çalışır.
Hypertable/continuous aggregate yok. Tablolar FK bağımlılığına göre sıralanır: ``firmalar``
önce (ortaklar/sozlesmeler/talepler ona referans verir), ``belgeler`` sürümlerden önce.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e1f4a2c3b567"
down_revision: str | None = "d5c8e1f0a927"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- CRM: firmalar (ortaklar/sozlesmeler/talepler referans verir → önce) ---
    op.create_table(
        "firmalar",
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("tip", sa.String(length=20), nullable=False, server_default="musteri"),
        sa.Column("vergi_no", sa.String(length=20), nullable=False, server_default=""),
        sa.Column("vergi_dairesi", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("telefon", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("eposta", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("adres", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("il", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("sektor", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("web_sitesi", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("sorumlu_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("aciklama", sa.String(length=2000), nullable=False, server_default=""),
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
            name=op.f("fk_firmalar_sorumlu_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_firmalar")),
    )
    op.create_index(op.f("ix_firmalar_ad"), "firmalar", ["ad"], unique=False)
    op.create_index(op.f("ix_firmalar_tip"), "firmalar", ["tip"], unique=False)
    op.create_index(op.f("ix_firmalar_sektor"), "firmalar", ["sektor"], unique=False)
    op.create_index(
        op.f("ix_firmalar_sorumlu_kullanici_id"),
        "firmalar",
        ["sorumlu_kullanici_id"],
        unique=False,
    )

    # --- CRM: ortaklar ---
    op.create_table(
        "ortaklar",
        sa.Column("firma_id", sa.BigInteger(), nullable=False),
        sa.Column("ad_soyad", sa.String(length=200), nullable=False),
        sa.Column("unvan", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("telefon", sa.String(length=30), nullable=False, server_default=""),
        sa.Column("eposta", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("birincil", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
            ["firma_id"],
            ["firmalar.id"],
            name=op.f("fk_ortaklar_firma_id_firmalar"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ortaklar")),
    )
    op.create_index(op.f("ix_ortaklar_firma_id"), "ortaklar", ["firma_id"], unique=False)

    # --- Sözleşme: sozlesmeler ---
    op.create_table(
        "sozlesmeler",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("firma_id", sa.BigInteger(), nullable=False),
        sa.Column("baslik", sa.String(length=200), nullable=False),
        sa.Column("tur", sa.String(length=20), nullable=False, server_default="hizmet"),
        sa.Column("baslangic_tarihi", sa.Date(), nullable=False),
        sa.Column("bitis_tarihi", sa.Date(), nullable=False),
        sa.Column("tutar", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("para_birimi", sa.String(length=3), nullable=False, server_default="TRY"),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="taslak"),
        sa.Column("sorumlu_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "yaklasim_bildirildi", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("aciklama", sa.String(length=2000), nullable=False, server_default=""),
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
            ["firma_id"],
            ["firmalar.id"],
            name=op.f("fk_sozlesmeler_firma_id_firmalar"),
        ),
        sa.ForeignKeyConstraint(
            ["sorumlu_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_sozlesmeler_sorumlu_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sozlesmeler")),
    )
    op.create_index(op.f("ix_sozlesmeler_kod"), "sozlesmeler", ["kod"], unique=True)
    op.create_index(op.f("ix_sozlesmeler_firma_id"), "sozlesmeler", ["firma_id"], unique=False)
    op.create_index(
        op.f("ix_sozlesmeler_bitis_tarihi"), "sozlesmeler", ["bitis_tarihi"], unique=False
    )
    op.create_index(op.f("ix_sozlesmeler_durum"), "sozlesmeler", ["durum"], unique=False)
    op.create_index(
        op.f("ix_sozlesmeler_sorumlu_kullanici_id"),
        "sozlesmeler",
        ["sorumlu_kullanici_id"],
        unique=False,
    )

    # --- Talep: talepler ---
    op.create_table(
        "talepler",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("firma_id", sa.BigInteger(), nullable=True),
        sa.Column("baslik", sa.String(length=200), nullable=False),
        sa.Column("aciklama", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("tur", sa.String(length=20), nullable=False, server_default="destek"),
        sa.Column("oncelik", sa.String(length=10), nullable=False, server_default="orta"),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="acik"),
        sa.Column("atanan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("talep_eden_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("talep_eden_ad", sa.String(length=200), nullable=False, server_default=""),
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
            ["firma_id"],
            ["firmalar.id"],
            name=op.f("fk_talepler_firma_id_firmalar"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["atanan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_talepler_atanan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["talep_eden_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_talepler_talep_eden_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_talepler")),
    )
    op.create_index(op.f("ix_talepler_kod"), "talepler", ["kod"], unique=True)
    op.create_index(op.f("ix_talepler_firma_id"), "talepler", ["firma_id"], unique=False)
    op.create_index(op.f("ix_talepler_oncelik"), "talepler", ["oncelik"], unique=False)
    op.create_index(op.f("ix_talepler_durum"), "talepler", ["durum"], unique=False)
    op.create_index(
        op.f("ix_talepler_atanan_kullanici_id"),
        "talepler",
        ["atanan_kullanici_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_talepler_talep_eden_kullanici_id"),
        "talepler",
        ["talep_eden_kullanici_id"],
        unique=False,
    )

    # --- DYS: belgeler (belge_surumleri referans verir → önce) ---
    op.create_table(
        "belgeler",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("kategori", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("aciklama", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("guncel_surum", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("aktif", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
            name=op.f("fk_belgeler_olusturan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_belgeler")),
    )
    op.create_index(op.f("ix_belgeler_kod"), "belgeler", ["kod"], unique=True)
    op.create_index(op.f("ix_belgeler_ad"), "belgeler", ["ad"], unique=False)
    op.create_index(op.f("ix_belgeler_kategori"), "belgeler", ["kategori"], unique=False)
    op.create_index(
        op.f("ix_belgeler_olusturan_kullanici_id"),
        "belgeler",
        ["olusturan_kullanici_id"],
        unique=False,
    )

    # --- DYS: belge_surumleri ---
    op.create_table(
        "belge_surumleri",
        sa.Column("belge_id", sa.BigInteger(), nullable=False),
        sa.Column("surum_no", sa.Integer(), nullable=False),
        sa.Column("dosya_adi", sa.String(length=255), nullable=False),
        sa.Column(
            "icerik_tipi",
            sa.String(length=150),
            nullable=False,
            server_default="application/octet-stream",
        ),
        sa.Column("boyut", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("nesne_anahtari", sa.String(length=500), nullable=False),
        sa.Column("yukleyen_kullanici_id", sa.BigInteger(), nullable=True),
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
            ["belge_id"],
            ["belgeler.id"],
            name=op.f("fk_belge_surumleri_belge_id_belgeler"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["yukleyen_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_belge_surumleri_yukleyen_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_belge_surumleri")),
        sa.UniqueConstraint(
            "belge_id", "surum_no", name="uq_belge_surumleri_belge_id_surum_no"
        ),
    )
    op.create_index(
        op.f("ix_belge_surumleri_belge_id"), "belge_surumleri", ["belge_id"], unique=False
    )
    op.create_index(
        op.f("ix_belge_surumleri_yukleyen_kullanici_id"),
        "belge_surumleri",
        ["yukleyen_kullanici_id"],
        unique=False,
    )

    # --- Duyuru: duyurular ---
    op.create_table(
        "duyurular",
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("baslik", sa.String(length=200), nullable=False),
        sa.Column("icerik", sa.String(length=5000), nullable=False, server_default=""),
        sa.Column("onem", sa.String(length=20), nullable=False, server_default="bilgi"),
        sa.Column("yayinda", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "yayin_tarihi",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("bitis_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hedef_departman", sa.String(length=100), nullable=False, server_default=""),
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
            name=op.f("fk_duyurular_olusturan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_duyurular")),
    )
    op.create_index(op.f("ix_duyurular_kod"), "duyurular", ["kod"], unique=True)
    op.create_index(op.f("ix_duyurular_onem"), "duyurular", ["onem"], unique=False)
    op.create_index(op.f("ix_duyurular_yayinda"), "duyurular", ["yayinda"], unique=False)
    op.create_index(
        op.f("ix_duyurular_olusturan_kullanici_id"),
        "duyurular",
        ["olusturan_kullanici_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_duyurular_olusturan_kullanici_id"), table_name="duyurular")
    op.drop_index(op.f("ix_duyurular_yayinda"), table_name="duyurular")
    op.drop_index(op.f("ix_duyurular_onem"), table_name="duyurular")
    op.drop_index(op.f("ix_duyurular_kod"), table_name="duyurular")
    op.drop_table("duyurular")

    op.drop_index(
        op.f("ix_belge_surumleri_yukleyen_kullanici_id"), table_name="belge_surumleri"
    )
    op.drop_index(op.f("ix_belge_surumleri_belge_id"), table_name="belge_surumleri")
    op.drop_table("belge_surumleri")

    op.drop_index(op.f("ix_belgeler_olusturan_kullanici_id"), table_name="belgeler")
    op.drop_index(op.f("ix_belgeler_kategori"), table_name="belgeler")
    op.drop_index(op.f("ix_belgeler_ad"), table_name="belgeler")
    op.drop_index(op.f("ix_belgeler_kod"), table_name="belgeler")
    op.drop_table("belgeler")

    op.drop_index(op.f("ix_talepler_talep_eden_kullanici_id"), table_name="talepler")
    op.drop_index(op.f("ix_talepler_atanan_kullanici_id"), table_name="talepler")
    op.drop_index(op.f("ix_talepler_durum"), table_name="talepler")
    op.drop_index(op.f("ix_talepler_oncelik"), table_name="talepler")
    op.drop_index(op.f("ix_talepler_firma_id"), table_name="talepler")
    op.drop_index(op.f("ix_talepler_kod"), table_name="talepler")
    op.drop_table("talepler")

    op.drop_index(op.f("ix_sozlesmeler_sorumlu_kullanici_id"), table_name="sozlesmeler")
    op.drop_index(op.f("ix_sozlesmeler_durum"), table_name="sozlesmeler")
    op.drop_index(op.f("ix_sozlesmeler_bitis_tarihi"), table_name="sozlesmeler")
    op.drop_index(op.f("ix_sozlesmeler_firma_id"), table_name="sozlesmeler")
    op.drop_index(op.f("ix_sozlesmeler_kod"), table_name="sozlesmeler")
    op.drop_table("sozlesmeler")

    op.drop_index(op.f("ix_ortaklar_firma_id"), table_name="ortaklar")
    op.drop_table("ortaklar")

    op.drop_index(op.f("ix_firmalar_sorumlu_kullanici_id"), table_name="firmalar")
    op.drop_index(op.f("ix_firmalar_sektor"), table_name="firmalar")
    op.drop_index(op.f("ix_firmalar_tip"), table_name="firmalar")
    op.drop_index(op.f("ix_firmalar_ad"), table_name="firmalar")
    op.drop_table("firmalar")
