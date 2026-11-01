"""S29 finans & muhasebe: cari hesap, cari hareket, fatura + kalem, tahsilat/ödeme (ADR-0048).

Revision ID: f8a0c2e4b6d8
Revises: e6b8d0f2a4c6
Create Date: 2026-11-01 06:30:00.000000

Tenant şemasında; fan-out döngüsünde her aktif tenant şemasında çalışır.

- ``cari_hesaplar`` firma başına tek satır (``firma_id`` UNIQUE); ``bakiye`` kilit altında değişir.
- ``cari_hareketler.kaynak`` UNIQUE: aynı fatura/ödeme bakiyeye iki kez girmez.
- ``faturalar`` + ``fatura_kalemleri``; ``odenen_tutar`` 0 ile genel toplam arasında (CHECK).
- ``odemeler.idempotency_anahtari`` UNIQUE (istemci yeniden denemesi ikinci ödeme açmaz).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f8a0c2e4b6d8"
down_revision: str | None = "e6b8d0f2a4c6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_PARA = sa.Numeric(18, 2)


def _zaman() -> list[sa.Column]:
    return [
        sa.Column("olusturma_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("guncelleme_tarihi", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    ]


def _id() -> sa.Column:
    return sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False)


def upgrade() -> None:
    op.create_table(
        "cari_hesaplar",
        _id(),
        sa.Column("firma_id", sa.BigInteger(), nullable=False),
        sa.Column("para_birimi", sa.String(length=3), server_default="TRY", nullable=False),
        sa.Column("bakiye", _PARA, server_default="0", nullable=False),
        *_zaman(),
        sa.ForeignKeyConstraint(["firma_id"], ["firmalar.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("firma_id", name="uq_cari_hesaplar_firma_id"),
    )

    op.create_table(
        "cari_hareketler",
        _id(),
        sa.Column("cari_id", sa.BigInteger(), nullable=False),
        sa.Column("tur", sa.String(length=20), nullable=False),
        sa.Column("tutar", _PARA, nullable=False),
        sa.Column("bakiye_sonrasi", _PARA, nullable=False),
        sa.Column("tarih", sa.Date(), nullable=False),
        sa.Column("kaynak", sa.String(length=60), nullable=False),
        sa.Column("aciklama", sa.String(length=500), server_default="", nullable=False),
        sa.Column("kullanici_id", sa.BigInteger(), nullable=True),
        *_zaman(),
        sa.ForeignKeyConstraint(["cari_id"], ["cari_hesaplar.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["kullanici_id"], ["kullanici.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kaynak", name="uq_cari_hareketler_kaynak"),
    )
    op.create_index("ix_cari_hareketler_cari_id", "cari_hareketler", ["cari_id"])
    op.create_index("ix_cari_hareketler_tarih", "cari_hareketler", ["tarih"])

    op.create_table(
        "faturalar",
        _id(),
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("tur", sa.String(length=10), nullable=False),
        sa.Column("firma_id", sa.BigInteger(), nullable=False),
        sa.Column("durum", sa.String(length=20), server_default="taslak", nullable=False),
        sa.Column("fatura_tarihi", sa.Date(), nullable=False),
        sa.Column("vade_tarihi", sa.Date(), nullable=False),
        sa.Column("para_birimi", sa.String(length=3), server_default="TRY", nullable=False),
        sa.Column("ara_toplam", _PARA, server_default="0", nullable=False),
        sa.Column("kdv_toplam", _PARA, server_default="0", nullable=False),
        sa.Column("genel_toplam", _PARA, server_default="0", nullable=False),
        sa.Column("odenen_tutar", _PARA, server_default="0", nullable=False),
        sa.Column("aciklama", sa.String(length=1000), server_default="", nullable=False),
        sa.Column("iade_nedeni", sa.String(length=500), server_default="", nullable=False),
        sa.Column("iptal_nedeni", sa.String(length=500), server_default="", nullable=False),
        sa.Column("satinalma_siparisi_id", sa.BigInteger(), nullable=True),
        sa.Column("olusturan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("kesen_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("kesim_tarihi", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ettn", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("senaryo", sa.String(length=20), server_default="TEMELFATURA", nullable=False),
        sa.Column("gib_durumu", sa.String(length=20), server_default="gonderilmedi", nullable=False),
        *_zaman(),
        sa.ForeignKeyConstraint(["firma_id"], ["firmalar.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["satinalma_siparisi_id"], ["satinalma_siparisleri.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["olusturan_kullanici_id"], ["kullanici.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["kesen_kullanici_id"], ["kullanici.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ettn", name="uq_faturalar_ettn"),
        sa.CheckConstraint("odenen_tutar >= 0", name="ck_faturalar_odenen"),
        sa.CheckConstraint("odenen_tutar <= genel_toplam", name="ck_faturalar_odenen_ust"),
    )
    op.create_index("ix_faturalar_kod", "faturalar", ["kod"], unique=True)
    op.create_index("ix_faturalar_tur", "faturalar", ["tur"])
    op.create_index("ix_faturalar_firma_id", "faturalar", ["firma_id"])
    op.create_index("ix_faturalar_durum", "faturalar", ["durum"])
    op.create_index("ix_faturalar_fatura_tarihi", "faturalar", ["fatura_tarihi"])
    op.create_index("ix_faturalar_vade_tarihi", "faturalar", ["vade_tarihi"])
    op.create_index("ix_faturalar_olusturan_kullanici_id", "faturalar", ["olusturan_kullanici_id"])

    op.create_table(
        "fatura_kalemleri",
        _id(),
        sa.Column("fatura_id", sa.BigInteger(), nullable=False),
        sa.Column("sira", sa.Integer(), nullable=False),
        sa.Column("aciklama", sa.String(length=300), nullable=False),
        sa.Column("malzeme_id", sa.BigInteger(), nullable=True),
        sa.Column("miktar", sa.Numeric(14, 3), nullable=False),
        sa.Column("birim", sa.String(length=20), server_default="adet", nullable=False),
        sa.Column("birim_fiyat", sa.Numeric(18, 4), nullable=False),
        sa.Column("kdv_orani", sa.Integer(), server_default="20", nullable=False),
        sa.Column("satir_tutari", _PARA, nullable=False),
        sa.Column("kdv_tutari", _PARA, nullable=False),
        *_zaman(),
        sa.ForeignKeyConstraint(["fatura_id"], ["faturalar.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["malzeme_id"], ["malzemeler.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("miktar > 0", name="ck_fatura_kalemleri_miktar"),
    )
    op.create_index("ix_fatura_kalemleri_fatura_id", "fatura_kalemleri", ["fatura_id"])

    op.create_table(
        "odemeler",
        _id(),
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("tur", sa.String(length=10), nullable=False),
        sa.Column("firma_id", sa.BigInteger(), nullable=False),
        sa.Column("fatura_id", sa.BigInteger(), nullable=True),
        sa.Column("tarih", sa.Date(), nullable=False),
        sa.Column("tutar", _PARA, nullable=False),
        sa.Column("yontem", sa.String(length=20), server_default="havale", nullable=False),
        sa.Column("aciklama", sa.String(length=500), server_default="", nullable=False),
        sa.Column("idempotency_anahtari", sa.String(length=80), nullable=True),
        sa.Column("kullanici_id", sa.BigInteger(), nullable=True),
        *_zaman(),
        sa.ForeignKeyConstraint(["firma_id"], ["firmalar.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["fatura_id"], ["faturalar.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["kullanici_id"], ["kullanici.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_anahtari", name="uq_odemeler_idempotency_anahtari"),
        sa.CheckConstraint("tutar > 0", name="ck_odemeler_tutar"),
    )
    op.create_index("ix_odemeler_kod", "odemeler", ["kod"], unique=True)
    op.create_index("ix_odemeler_tur", "odemeler", ["tur"])
    op.create_index("ix_odemeler_firma_id", "odemeler", ["firma_id"])
    op.create_index("ix_odemeler_fatura_id", "odemeler", ["fatura_id"])
    op.create_index("ix_odemeler_tarih", "odemeler", ["tarih"])


def downgrade() -> None:
    op.drop_table("odemeler")
    op.drop_table("fatura_kalemleri")
    op.drop_table("faturalar")
    op.drop_table("cari_hareketler")
    op.drop_table("cari_hesaplar")
