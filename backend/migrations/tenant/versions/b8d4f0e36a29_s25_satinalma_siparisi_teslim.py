"""S25-B tedarik zinciri: satınalma siparişi (PO) → teslim alma → iade (ADR-0024 §3, §4b).

Revision ID: b8d4f0e36a29
Revises: a7c3e9d25f18
Create Date: 2026-11-01 01:00:00.000000

Tenant şemasında; fan-out döngüsünde her aktif tenant şemasında çalışır.

- ``satinalma_siparisleri`` yalnız ONAYLANMIŞ talepten açılır (talep onayı = görev ayrımı);
  bir talebin iptal edilmemiş en çok bir siparişi olur (kısmi UNIQUE indeks).
- ``satinalma_siparisi_kalemleri.teslim_alinan_miktar`` tutulan kümülatif değerdir; fazla
  teslim toleransı kalem başınadır, varsayılan 0 (katı).
- ``teslim_almalar`` başlık (irsaliye), ``teslim_alma_kalemleri`` satır. Aynı siparişte aynı
  irsaliye ikinci kez işlenmez: ``(siparis_id, irsaliye_no, tur)`` UNIQUE. İade, orijinal
  teslime ``iade_edilen_id`` ile bağlı ters kayıttır.
- ``stok_hareketleri.hizli_kabul``: PO'suz hızlı mal kabul (§4b). Resmî teslim alma eşleşmemiş
  hızlı girişi bulursa yeni hareket yazmaz, onu ``eslesen_hareket_id`` ile bağlar.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8d4f0e36a29"
down_revision: str | None = "a7c3e9d25f18"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MIKTAR = sa.Numeric(18, 3)
_PARA = sa.Numeric(18, 2)


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
    op.create_table(
        "satinalma_siparisleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("talep_id", sa.BigInteger(), nullable=False),
        sa.Column("tedarikci_firma_id", sa.BigInteger(), nullable=False),
        sa.Column("durum", sa.String(length=20), server_default="acik", nullable=False),
        sa.Column("para_birimi", sa.String(length=3), server_default="TRY", nullable=False),
        sa.Column("beklenen_teslim_tarihi", sa.Date(), nullable=True),
        sa.Column("aciklama", sa.String(length=1000), server_default="", nullable=False),
        sa.Column("olusturan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("kapanis_nedeni", sa.String(length=500), nullable=True),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["talep_id"], ["satinalma_talepleri.id"],
            name=op.f("fk_satinalma_siparisleri_talep_id_satinalma_talepleri"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["tedarikci_firma_id"], ["firmalar.id"],
            name=op.f("fk_satinalma_siparisleri_tedarikci_firma_id_firmalar"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["olusturan_kullanici_id"], ["kullanici.id"],
            name=op.f("fk_satinalma_siparisleri_olusturan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_satinalma_siparisleri")),
        sa.UniqueConstraint("kod", name=op.f("uq_satinalma_siparisleri_kod")),
    )
    op.create_index(
        op.f("ix_satinalma_siparisleri_tedarikci_firma_id"), "satinalma_siparisleri",
        ["tedarikci_firma_id"],
    )
    op.create_index(op.f("ix_satinalma_siparisleri_durum"), "satinalma_siparisleri", ["durum"])
    op.create_index(
        "uq_satinalma_siparisleri_aktif_talep", "satinalma_siparisleri", ["talep_id"],
        unique=True, postgresql_where=sa.text("durum <> 'iptal'"),
    )

    op.create_table(
        "satinalma_siparisi_kalemleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("siparis_id", sa.BigInteger(), nullable=False),
        sa.Column("talep_kalemi_id", sa.BigInteger(), nullable=True),
        sa.Column("malzeme_id", sa.BigInteger(), nullable=False),
        sa.Column("miktar", _MIKTAR, nullable=False),
        sa.Column("birim_fiyat", _PARA, nullable=True),
        sa.Column(
            "fazla_teslim_toleransi_yuzde", sa.Numeric(5, 2), server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("teslim_alinan_miktar", _MIKTAR, server_default=sa.text("0"), nullable=False),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["siparis_id"], ["satinalma_siparisleri.id"],
            name=op.f("fk_satinalma_siparisi_kalemleri_siparis_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["talep_kalemi_id"], ["satinalma_talebi_kalemleri.id"],
            name=op.f("fk_satinalma_siparisi_kalemleri_talep_kalemi_id"), ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["malzeme_id"], ["malzemeler.id"],
            name=op.f("fk_satinalma_siparisi_kalemleri_malzeme_id_malzemeler"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_satinalma_siparisi_kalemleri")),
        sa.CheckConstraint("miktar > 0", name=op.f("ck_satinalma_siparisi_kalemleri_miktar")),
        sa.CheckConstraint(
            "teslim_alinan_miktar >= 0", name=op.f("ck_satinalma_siparisi_kalemleri_teslim")
        ),
        sa.CheckConstraint(
            "fazla_teslim_toleransi_yuzde >= 0 AND fazla_teslim_toleransi_yuzde <= 100",
            name=op.f("ck_satinalma_siparisi_kalemleri_tolerans"),
        ),
    )
    op.create_index(
        op.f("ix_satinalma_siparisi_kalemleri_siparis_id"), "satinalma_siparisi_kalemleri",
        ["siparis_id"],
    )

    op.create_table(
        "teslim_almalar",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("siparis_id", sa.BigInteger(), nullable=False),
        sa.Column("tur", sa.String(length=10), server_default="teslim", nullable=False),
        sa.Column("irsaliye_no", sa.String(length=40), nullable=False),
        sa.Column("iade_edilen_id", sa.BigInteger(), nullable=True),
        sa.Column("fiili_tarih", sa.DateTime(timezone=True), nullable=False),
        sa.Column("zamaninda", sa.Boolean(), nullable=True),
        sa.Column("aciklama", sa.String(length=500), server_default="", nullable=False),
        sa.Column("idempotency_anahtari", sa.String(length=64), nullable=True),
        sa.Column("olusturan_kullanici_id", sa.BigInteger(), nullable=True),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["siparis_id"], ["satinalma_siparisleri.id"],
            name=op.f("fk_teslim_almalar_siparis_id_satinalma_siparisleri"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["iade_edilen_id"], ["teslim_almalar.id"],
            name=op.f("fk_teslim_almalar_iade_edilen_id_teslim_almalar"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["olusturan_kullanici_id"], ["kullanici.id"],
            name=op.f("fk_teslim_almalar_olusturan_kullanici_id_kullanici"), ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teslim_almalar")),
        sa.UniqueConstraint(
            "siparis_id", "irsaliye_no", "tur", name=op.f("uq_teslim_almalar_siparis_id")
        ),
        sa.UniqueConstraint("idempotency_anahtari", name=op.f("uq_teslim_almalar_idempotency")),
        sa.CheckConstraint("tur IN ('teslim', 'iade')", name=op.f("ck_teslim_almalar_tur")),
    )
    op.create_index(op.f("ix_teslim_almalar_siparis_id"), "teslim_almalar", ["siparis_id"])

    op.create_table(
        "teslim_alma_kalemleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("teslim_id", sa.BigInteger(), nullable=False),
        sa.Column("siparis_kalemi_id", sa.BigInteger(), nullable=False),
        sa.Column("iade_edilen_kalem_id", sa.BigInteger(), nullable=True),
        sa.Column("miktar", _MIKTAR, nullable=False),
        sa.Column("lokasyon_id", sa.BigInteger(), nullable=False),
        sa.Column("lot_no", sa.String(length=60), server_default="", nullable=False),
        sa.Column("fazla_teslim", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("stok_hareketi_id", sa.BigInteger(), nullable=True),
        sa.Column("eslesen_hareket_id", sa.BigInteger(), nullable=True),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["teslim_id"], ["teslim_almalar.id"],
            name=op.f("fk_teslim_alma_kalemleri_teslim_id_teslim_almalar"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["siparis_kalemi_id"], ["satinalma_siparisi_kalemleri.id"],
            name=op.f("fk_teslim_alma_kalemleri_siparis_kalemi_id"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["iade_edilen_kalem_id"], ["teslim_alma_kalemleri.id"],
            name=op.f("fk_teslim_alma_kalemleri_iade_edilen_kalem_id"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lokasyon_id"], ["lokasyonlar.id"],
            name=op.f("fk_teslim_alma_kalemleri_lokasyon_id_lokasyonlar"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["stok_hareketi_id"], ["stok_hareketleri.id"],
            name=op.f("fk_teslim_alma_kalemleri_stok_hareketi_id"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["eslesen_hareket_id"], ["stok_hareketleri.id"],
            name=op.f("fk_teslim_alma_kalemleri_eslesen_hareket_id"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_teslim_alma_kalemleri")),
        sa.UniqueConstraint(
            "eslesen_hareket_id", name=op.f("uq_teslim_alma_kalemleri_eslesen_hareket_id")
        ),
        sa.CheckConstraint("miktar > 0", name=op.f("ck_teslim_alma_kalemleri_miktar")),
    )
    op.create_index(
        op.f("ix_teslim_alma_kalemleri_teslim_id"), "teslim_alma_kalemleri", ["teslim_id"]
    )
    op.create_index(
        op.f("ix_teslim_alma_kalemleri_siparis_kalemi_id"), "teslim_alma_kalemleri",
        ["siparis_kalemi_id"],
    )

    op.add_column("stok_hareketleri", sa.Column(
        "hizli_kabul", sa.Boolean(), server_default=sa.text("false"), nullable=False
    ))


def downgrade() -> None:
    op.drop_column("stok_hareketleri", "hizli_kabul")
    op.drop_index(
        op.f("ix_teslim_alma_kalemleri_siparis_kalemi_id"), table_name="teslim_alma_kalemleri"
    )
    op.drop_index(op.f("ix_teslim_alma_kalemleri_teslim_id"), table_name="teslim_alma_kalemleri")
    op.drop_table("teslim_alma_kalemleri")
    op.drop_index(op.f("ix_teslim_almalar_siparis_id"), table_name="teslim_almalar")
    op.drop_table("teslim_almalar")
    op.drop_index(
        op.f("ix_satinalma_siparisi_kalemleri_siparis_id"),
        table_name="satinalma_siparisi_kalemleri",
    )
    op.drop_table("satinalma_siparisi_kalemleri")
    op.drop_index("uq_satinalma_siparisleri_aktif_talep", table_name="satinalma_siparisleri")
    op.drop_index(op.f("ix_satinalma_siparisleri_durum"), table_name="satinalma_siparisleri")
    op.drop_index(
        op.f("ix_satinalma_siparisleri_tedarikci_firma_id"), table_name="satinalma_siparisleri"
    )
    op.drop_table("satinalma_siparisleri")
