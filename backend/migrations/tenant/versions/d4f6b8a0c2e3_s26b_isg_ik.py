"""S26-B İSG + İK kurumsal tamamlama (ADR-0044).

Revision ID: d4f6b8a0c2e3
Revises: c3e5a7f9b1d2
Create Date: 2026-11-01 03:30:00.000000

Tenant şemasında; fan-out döngüsünde her aktif tenant şemasında çalışır.

- İSG: ``isg_egitimleri`` + ``isg_egitim_katilimlari`` (eğitim × personel tekil),
  ``isg_egitim_gereksinimleri`` ve ``kkd_gereksinimleri`` (departman × konu/KKD tekil;
  ``departman=''`` herkese), ``acil_durum_tatbikatlari``.
- İK: ``personel.yonetici_id`` (org şeması), ``zimmetler.kategori`` (``kkd`` teslimi),
  ``personel_kontrol_listeleri`` (personel × tür tekil; maddeler JSONB).
- Kalite: ``uygunsuzluklar.kaynak_kaza_id`` UNIQUE (kaza başına tek CAPA vakası).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4f6b8a0c2e3"
down_revision: str | None = "c3e5a7f9b1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _zaman() -> list[sa.Column]:
    return [
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _id() -> sa.Column:
    return sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False)


def upgrade() -> None:
    op.create_table(
        "isg_egitimleri",
        _id(),
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("konu", sa.String(length=100), nullable=False),
        sa.Column("baslik", sa.String(length=200), nullable=False),
        sa.Column("tarih", sa.Date(), nullable=False),
        sa.Column("sure_saat", sa.Numeric(5, 1), server_default="0", nullable=False),
        sa.Column("egitmen", sa.String(length=200), server_default="", nullable=False),
        sa.Column("gecerlilik_ay", sa.Integer(), server_default="12", nullable=False),
        sa.Column("aciklama", sa.String(length=2000), server_default="", nullable=False),
        *_zaman(),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("gecerlilik_ay >= 0", name="ck_isg_egitimleri_gecerlilik"),
    )
    op.create_index("ix_isg_egitimleri_kod", "isg_egitimleri", ["kod"], unique=True)
    op.create_index("ix_isg_egitimleri_konu", "isg_egitimleri", ["konu"])
    op.create_index("ix_isg_egitimleri_tarih", "isg_egitimleri", ["tarih"])

    op.create_table(
        "isg_egitim_katilimlari",
        _id(),
        sa.Column("egitim_id", sa.BigInteger(), nullable=False),
        sa.Column("personel_id", sa.BigInteger(), nullable=False),
        *_zaman(),
        sa.ForeignKeyConstraint(["egitim_id"], ["isg_egitimleri.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["personel_id"], ["personel.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("egitim_id", "personel_id", name="uq_egitim_katilim"),
    )
    op.create_index("ix_isg_egitim_katilimlari_egitim_id", "isg_egitim_katilimlari", ["egitim_id"])
    op.create_index("ix_isg_egitim_katilimlari_personel_id", "isg_egitim_katilimlari", ["personel_id"])

    op.create_table(
        "isg_egitim_gereksinimleri",
        _id(),
        sa.Column("departman", sa.String(length=100), server_default="", nullable=False),
        sa.Column("konu", sa.String(length=100), nullable=False),
        *_zaman(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("departman", "konu", name="uq_egitim_gereksinimi"),
    )
    op.create_table(
        "kkd_gereksinimleri",
        _id(),
        sa.Column("departman", sa.String(length=100), server_default="", nullable=False),
        sa.Column("kkd", sa.String(length=200), nullable=False),
        *_zaman(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("departman", "kkd", name="uq_kkd_gereksinimi"),
    )

    op.create_table(
        "acil_durum_tatbikatlari",
        _id(),
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("tur", sa.String(length=30), nullable=False),
        sa.Column("tarih", sa.Date(), nullable=False),
        sa.Column("yer", sa.String(length=200), server_default="", nullable=False),
        sa.Column("katilimci_sayisi", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tahliye_suresi_sn", sa.Integer(), nullable=True),
        sa.Column("bulgular", sa.String(length=4000), server_default="", nullable=False),
        sa.Column("sonraki_tarih", sa.Date(), nullable=True),
        sa.Column("yurutucu_kullanici_id", sa.BigInteger(), nullable=True),
        *_zaman(),
        sa.ForeignKeyConstraint(["yurutucu_kullanici_id"], ["kullanici.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("katilimci_sayisi >= 0", name="ck_tatbikat_katilimci"),
    )
    op.create_index("ix_acil_durum_tatbikatlari_kod", "acil_durum_tatbikatlari", ["kod"], unique=True)
    op.create_index("ix_acil_durum_tatbikatlari_tur", "acil_durum_tatbikatlari", ["tur"])
    op.create_index("ix_acil_durum_tatbikatlari_tarih", "acil_durum_tatbikatlari", ["tarih"])
    op.create_index(
        "ix_acil_durum_tatbikatlari_yurutucu_kullanici_id", "acil_durum_tatbikatlari", ["yurutucu_kullanici_id"]
    )

    op.add_column("personel", sa.Column("yonetici_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_personel_yonetici_id", "personel", "personel", ["yonetici_id"], ["id"], ondelete="SET NULL"
    )
    op.create_index("ix_personel_yonetici_id", "personel", ["yonetici_id"])

    op.add_column("zimmetler", sa.Column("kategori", sa.String(length=20), server_default="demirbas", nullable=False))
    op.create_index("ix_zimmetler_kategori", "zimmetler", ["kategori"])

    op.create_table(
        "personel_kontrol_listeleri",
        _id(),
        sa.Column("personel_id", sa.BigInteger(), nullable=False),
        sa.Column("tur", sa.String(length=10), nullable=False),
        sa.Column("maddeler", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("durum", sa.String(length=20), server_default="acik", nullable=False),
        sa.Column("tamamlanma_tarihi", sa.DateTime(timezone=True), nullable=True),
        *_zaman(),
        sa.ForeignKeyConstraint(["personel_id"], ["personel.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("personel_id", "tur", name="uq_personel_kontrol_listesi"),
        sa.CheckConstraint("tur IN ('giris', 'cikis')", name="ck_kontrol_listesi_tur"),
    )
    op.create_index("ix_personel_kontrol_listeleri_personel_id", "personel_kontrol_listeleri", ["personel_id"])
    op.create_index("ix_personel_kontrol_listeleri_durum", "personel_kontrol_listeleri", ["durum"])

    op.add_column("uygunsuzluklar", sa.Column("kaynak_kaza_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_uygunsuzluklar_kaynak_kaza_id",
        "uygunsuzluklar",
        "is_kazalari",
        ["kaynak_kaza_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_uygunsuzluklar_kaynak_kaza_id", "uygunsuzluklar", ["kaynak_kaza_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_uygunsuzluklar_kaynak_kaza_id", table_name="uygunsuzluklar")
    op.drop_constraint("fk_uygunsuzluklar_kaynak_kaza_id", "uygunsuzluklar", type_="foreignkey")
    op.drop_column("uygunsuzluklar", "kaynak_kaza_id")
    op.drop_table("personel_kontrol_listeleri")
    op.drop_index("ix_zimmetler_kategori", table_name="zimmetler")
    op.drop_column("zimmetler", "kategori")
    op.drop_index("ix_personel_yonetici_id", table_name="personel")
    op.drop_constraint("fk_personel_yonetici_id", "personel", type_="foreignkey")
    op.drop_column("personel", "yonetici_id")
    op.drop_table("acil_durum_tatbikatlari")
    op.drop_table("kkd_gereksinimleri")
    op.drop_table("isg_egitim_gereksinimleri")
    op.drop_table("isg_egitim_katilimlari")
    op.drop_table("isg_egitimleri")
