"""S26-A kalite olgunluğu: ölçüm cihazı + kalibrasyon, kontrol planı + SPC (ADR-0025).

Revision ID: c3e5a7f9b1d2
Revises: b8d4f0e36a29
Create Date: 2026-11-01 02:30:00.000000

Tenant şemasında; fan-out döngüsünde her aktif tenant şemasında çalışır.

- ``olcum_cihazlari`` geçerliliği ``sonraki_kalibrasyon_tarihi``nden okunur; kenar tetikli
  hatırlatma bayrağı ``yaklasim_bildirildi`` (yeni kalibrasyon kaydı sıfırlar).
- ``spc_alt_gruplari`` karakteristik başına sıralı (``(karakteristik_id, sira)`` UNIQUE); değerler
  JSONB dizi (alt grup boyutu 2–10, X̄-R kartı).
- ``uygunsuzluklar.tedarikci_firma_id``: giriş muayenesinde kaynağın tedarikçi olması.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c3e5a7f9b1d2"
down_revision: str | None = "b8d4f0e36a29"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLCU = sa.Numeric(18, 3)


def _zaman() -> list[sa.Column]:
    return [
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "olcum_cihazlari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("tur", sa.String(length=100), server_default="", nullable=False),
        sa.Column("seri_no", sa.String(length=100), server_default="", nullable=False),
        sa.Column("konum", sa.String(length=200), server_default="", nullable=False),
        sa.Column("kalibrasyon_periyodu_gun", sa.Integer(), server_default="365", nullable=False),
        sa.Column("son_kalibrasyon_tarihi", sa.Date(), nullable=True),
        sa.Column("sonraki_kalibrasyon_tarihi", sa.Date(), nullable=True),
        sa.Column("durum", sa.String(length=20), server_default="aktif", nullable=False),
        sa.Column("sorumlu_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("yaklasim_bildirildi", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        *_zaman(),
        sa.ForeignKeyConstraint(["sorumlu_kullanici_id"], ["kullanici.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("kalibrasyon_periyodu_gun > 0", name="ck_olcum_cihazlari_periyot"),
    )
    op.create_index("ix_olcum_cihazlari_kod", "olcum_cihazlari", ["kod"], unique=True)
    op.create_index("ix_olcum_cihazlari_durum", "olcum_cihazlari", ["durum"])
    op.create_index(
        "ix_olcum_cihazlari_sonraki_kalibrasyon_tarihi", "olcum_cihazlari", ["sonraki_kalibrasyon_tarihi"]
    )

    op.create_table(
        "kalibrasyon_kayitlari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("cihaz_id", sa.BigInteger(), nullable=False),
        sa.Column("tarih", sa.Date(), nullable=False),
        sa.Column("sonuc", sa.String(length=20), nullable=False),
        sa.Column("sertifika_no", sa.String(length=100), server_default="", nullable=False),
        sa.Column("kurum", sa.String(length=200), server_default="", nullable=False),
        sa.Column("aciklama", sa.String(length=1000), server_default="", nullable=False),
        sa.Column("belge_id", sa.BigInteger(), nullable=True),
        sa.Column("kaydeden_kullanici_id", sa.BigInteger(), nullable=True),
        *_zaman(),
        sa.ForeignKeyConstraint(["cihaz_id"], ["olcum_cihazlari.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["belge_id"], ["belgeler.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["kaydeden_kullanici_id"], ["kullanici.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kalibrasyon_kayitlari_cihaz_id", "kalibrasyon_kayitlari", ["cihaz_id"])

    op.create_table(
        "kontrol_planlari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("urun_id", sa.BigInteger(), nullable=True),
        sa.Column("operasyon", sa.String(length=200), server_default="", nullable=False),
        sa.Column("aciklama", sa.String(length=1000), server_default="", nullable=False),
        sa.Column("aktif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("olusturan_kullanici_id", sa.BigInteger(), nullable=True),
        *_zaman(),
        sa.ForeignKeyConstraint(["urun_id"], ["urunler.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["olusturan_kullanici_id"], ["kullanici.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kontrol_planlari_kod", "kontrol_planlari", ["kod"], unique=True)
    op.create_index("ix_kontrol_planlari_urun_id", "kontrol_planlari", ["urun_id"])

    op.create_table(
        "kontrol_karakteristikleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.BigInteger(), nullable=False),
        sa.Column("sira", sa.Integer(), server_default="1", nullable=False),
        sa.Column("ad", sa.String(length=200), nullable=False),
        sa.Column("birim", sa.String(length=20), server_default="mm", nullable=False),
        sa.Column("nominal", _OLCU, nullable=True),
        sa.Column("alt_tolerans", _OLCU, nullable=True),
        sa.Column("ust_tolerans", _OLCU, nullable=True),
        sa.Column("alt_grup_boyutu", sa.Integer(), server_default="5", nullable=False),
        sa.Column("olcum_yontemi", sa.String(length=500), server_default="", nullable=False),
        sa.Column("cihaz_id", sa.BigInteger(), nullable=True),
        sa.Column("sabit_limitler", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        *_zaman(),
        sa.ForeignKeyConstraint(["plan_id"], ["kontrol_planlari.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cihaz_id"], ["olcum_cihazlari.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("alt_grup_boyutu BETWEEN 2 AND 10", name="ck_kontrol_karakteristikleri_n"),
        sa.CheckConstraint(
            "alt_tolerans IS NULL OR ust_tolerans IS NULL OR alt_tolerans < ust_tolerans",
            name="ck_kontrol_karakteristikleri_tolerans",
        ),
    )
    op.create_index("ix_kontrol_karakteristikleri_plan_id", "kontrol_karakteristikleri", ["plan_id"])

    op.create_table(
        "spc_alt_gruplari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("karakteristik_id", sa.BigInteger(), nullable=False),
        sa.Column("sira", sa.Integer(), nullable=False),
        sa.Column("zaman", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("degerler", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("cihaz_id", sa.BigInteger(), nullable=True),
        sa.Column("olcen_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("ihlaller", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False),
        sa.Column("aciklama", sa.String(length=500), server_default="", nullable=False),
        *_zaman(),
        sa.ForeignKeyConstraint(["karakteristik_id"], ["kontrol_karakteristikleri.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cihaz_id"], ["olcum_cihazlari.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["olcen_kullanici_id"], ["kullanici.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("karakteristik_id", "sira", name="uq_spc_alt_gruplari_sira"),
    )
    op.create_index("ix_spc_alt_gruplari_karakteristik_id", "spc_alt_gruplari", ["karakteristik_id"])

    op.add_column("uygunsuzluklar", sa.Column("tedarikci_firma_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_uygunsuzluklar_tedarikci_firma_id",
        "uygunsuzluklar",
        "firmalar",
        ["tedarikci_firma_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_uygunsuzluklar_tedarikci_firma_id", "uygunsuzluklar", ["tedarikci_firma_id"])


def downgrade() -> None:
    op.drop_index("ix_uygunsuzluklar_tedarikci_firma_id", table_name="uygunsuzluklar")
    op.drop_constraint("fk_uygunsuzluklar_tedarikci_firma_id", "uygunsuzluklar", type_="foreignkey")
    op.drop_column("uygunsuzluklar", "tedarikci_firma_id")
    op.drop_table("spc_alt_gruplari")
    op.drop_table("kontrol_karakteristikleri")
    op.drop_table("kontrol_planlari")
    op.drop_table("kalibrasyon_kayitlari")
    op.drop_table("olcum_cihazlari")
