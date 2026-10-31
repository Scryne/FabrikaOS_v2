"""S25-A tedarik zinciri: depo/lokasyon + lokasyon bakiyesi + transfer + sayım (ADR-0024).

Revision ID: a7c3e9d25f18
Revises: f4c8a2e6b791
Create Date: 2026-10-31 21:00:00.000000

Tenant şemasında; fan-out döngüsünde her aktif tenant şemasında çalışır.

- ``stok_bakiyeleri(malzeme_id, lokasyon_id, lot_no)`` UNIQUE — bakiye anahtarı baştan üç
  boyutlu (ADR-0024 §4): ``lot_no = ''`` "lot takibi yok" demektir; lot gelince yapı değişmez.
- ``stok_hareketleri`` lokasyon, lot ve transfer grubu kazanır; ``tur`` 10 → 20 karakter
  (``transfer_cikis``, ``sayim_duzeltme``).
- **Geri doldurma (veri kaybı yok):** her şemaya varsayılan ``ANA`` deposu ve ``GENEL``
  lokasyonu açılır; sıfırdan farklı her ``malzemeler.mevcut_miktar`` o lokasyona bakiye olarak
  yazılır, mevcut hareketler o lokasyona bağlanır. ``Malzeme.mevcut_miktar`` korunur ve artık
  lokasyon bakiyelerinin toplamıdır (eski ekranlar, kritik stok olayı, MRP onu okur).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c3e9d25f18"
down_revision: str | None = "f4c8a2e6b791"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_MIKTAR = sa.Numeric(18, 3)


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
        "depolar",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kod", sa.String(length=30), nullable=False),
        sa.Column("ad", sa.String(length=120), nullable=False),
        sa.Column("adres", sa.String(length=300), server_default="", nullable=False),
        sa.Column("aktif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_zaman_damgalari(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_depolar")),
        sa.UniqueConstraint("kod", name=op.f("uq_depolar_kod")),
    )
    op.create_table(
        "lokasyonlar",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("depo_id", sa.BigInteger(), nullable=False),
        sa.Column("ust_lokasyon_id", sa.BigInteger(), nullable=True),
        sa.Column("kod", sa.String(length=40), nullable=False),
        sa.Column("ad", sa.String(length=120), nullable=False),
        sa.Column("aktif", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["depo_id"], ["depolar.id"], name=op.f("fk_lokasyonlar_depo_id_depolar"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["ust_lokasyon_id"], ["lokasyonlar.id"],
            name=op.f("fk_lokasyonlar_ust_lokasyon_id_lokasyonlar"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_lokasyonlar")),
        sa.UniqueConstraint("depo_id", "kod", name=op.f("uq_lokasyonlar_depo_id")),
    )
    op.create_index(op.f("ix_lokasyonlar_depo_id"), "lokasyonlar", ["depo_id"])

    op.create_table(
        "stok_bakiyeleri",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("malzeme_id", sa.BigInteger(), nullable=False),
        sa.Column("lokasyon_id", sa.BigInteger(), nullable=False),
        sa.Column("lot_no", sa.String(length=60), server_default="", nullable=False),
        sa.Column("miktar", _MIKTAR, server_default=sa.text("0"), nullable=False),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["malzeme_id"], ["malzemeler.id"],
            name=op.f("fk_stok_bakiyeleri_malzeme_id_malzemeler"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["lokasyon_id"], ["lokasyonlar.id"],
            name=op.f("fk_stok_bakiyeleri_lokasyon_id_lokasyonlar"), ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_stok_bakiyeleri")),
        sa.UniqueConstraint(
            "malzeme_id", "lokasyon_id", "lot_no", name=op.f("uq_stok_bakiyeleri_malzeme_id")
        ),
        sa.CheckConstraint("miktar >= 0", name=op.f("ck_stok_bakiyeleri_negatif_degil")),
    )
    op.create_index(op.f("ix_stok_bakiyeleri_lokasyon_id"), "stok_bakiyeleri", ["lokasyon_id"])

    op.create_table(
        "sayim_oturumlari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kod", sa.String(length=40), nullable=False),
        sa.Column("lokasyon_id", sa.BigInteger(), nullable=False),
        sa.Column("durum", sa.String(length=20), server_default="acik", nullable=False),
        sa.Column("aciklama", sa.String(length=500), server_default="", nullable=False),
        sa.Column("olusturan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("onaylayan_kullanici_id", sa.BigInteger(), nullable=True),
        sa.Column("onay_tarihi", sa.DateTime(timezone=True), nullable=True),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["lokasyon_id"], ["lokasyonlar.id"],
            name=op.f("fk_sayim_oturumlari_lokasyon_id_lokasyonlar"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["olusturan_kullanici_id"], ["kullanici.id"],
            name=op.f("fk_sayim_oturumlari_olusturan_kullanici_id_kullanici"), ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["onaylayan_kullanici_id"], ["kullanici.id"],
            name=op.f("fk_sayim_oturumlari_onaylayan_kullanici_id_kullanici"), ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sayim_oturumlari")),
        sa.UniqueConstraint("kod", name=op.f("uq_sayim_oturumlari_kod")),
    )
    op.create_table(
        "sayim_satirlari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("oturum_id", sa.BigInteger(), nullable=False),
        sa.Column("malzeme_id", sa.BigInteger(), nullable=False),
        sa.Column("lot_no", sa.String(length=60), server_default="", nullable=False),
        sa.Column("sistem_miktari", _MIKTAR, nullable=False),
        sa.Column("sayilan_miktar", _MIKTAR, nullable=False),
        sa.Column("uygulanan_hareket_id", sa.BigInteger(), nullable=True),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["oturum_id"], ["sayim_oturumlari.id"],
            name=op.f("fk_sayim_satirlari_oturum_id_sayim_oturumlari"), ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["malzeme_id"], ["malzemeler.id"],
            name=op.f("fk_sayim_satirlari_malzeme_id_malzemeler"), ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["uygulanan_hareket_id"], ["stok_hareketleri.id"],
            name=op.f("fk_sayim_satirlari_uygulanan_hareket_id_stok_hareketleri"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sayim_satirlari")),
        sa.UniqueConstraint(
            "oturum_id", "malzeme_id", "lot_no", name=op.f("uq_sayim_satirlari_oturum_id")
        ),
        sa.CheckConstraint("sayilan_miktar >= 0", name=op.f("ck_sayim_satirlari_sayilan")),
    )

    op.add_column("malzemeler", sa.Column(
        "lot_takipli", sa.Boolean(), server_default=sa.text("false"), nullable=False
    ))
    op.alter_column("stok_hareketleri", "tur", type_=sa.String(length=20),
                    existing_type=sa.String(length=10), existing_nullable=False)
    op.add_column("stok_hareketleri", sa.Column("lokasyon_id", sa.BigInteger(), nullable=True))
    op.add_column("stok_hareketleri", sa.Column(
        "lot_no", sa.String(length=60), server_default="", nullable=False
    ))
    op.add_column("stok_hareketleri", sa.Column("transfer_grubu", sa.String(length=36),
                                                nullable=True))
    op.create_foreign_key(
        op.f("fk_stok_hareketleri_lokasyon_id_lokasyonlar"), "stok_hareketleri", "lokasyonlar",
        ["lokasyon_id"], ["id"], ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_stok_hareketleri_lokasyon_id"), "stok_hareketleri", ["lokasyon_id"])
    op.create_index(
        op.f("ix_stok_hareketleri_transfer_grubu"), "stok_hareketleri", ["transfer_grubu"]
    )

    # --- geri doldurma: varsayılan depo/lokasyon + mevcut bakiyeler ---
    op.execute("INSERT INTO depolar (kod, ad) VALUES ('ANA', 'Ana depo')")
    op.execute(
        "INSERT INTO lokasyonlar (depo_id, kod, ad) "
        "SELECT id, 'GENEL', 'Genel alan' FROM depolar WHERE kod = 'ANA'"
    )
    op.execute(
        "INSERT INTO stok_bakiyeleri (malzeme_id, lokasyon_id, lot_no, miktar) "
        "SELECT m.id, l.id, '', m.mevcut_miktar FROM malzemeler m "
        "CROSS JOIN lokasyonlar l JOIN depolar d ON d.id = l.depo_id "
        "WHERE d.kod = 'ANA' AND l.kod = 'GENEL' AND m.mevcut_miktar <> 0"
    )
    op.execute(
        "UPDATE stok_hareketleri SET lokasyon_id = l.id FROM lokasyonlar l "
        "JOIN depolar d ON d.id = l.depo_id WHERE d.kod = 'ANA' AND l.kod = 'GENEL'"
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_stok_hareketleri_transfer_grubu"), table_name="stok_hareketleri")
    op.drop_index(op.f("ix_stok_hareketleri_lokasyon_id"), table_name="stok_hareketleri")
    op.drop_constraint(
        op.f("fk_stok_hareketleri_lokasyon_id_lokasyonlar"), "stok_hareketleri",
        type_="foreignkey",
    )
    op.drop_column("stok_hareketleri", "transfer_grubu")
    op.drop_column("stok_hareketleri", "lot_no")
    op.drop_column("stok_hareketleri", "lokasyon_id")
    # ``tur`` 20 karakterde BIRAKILIR: transfer/sayım hareketleri ("transfer_cikis",
    # "sayim_duzeltme") 10 karakteri aşar ve daraltma ya geri dönüşü durdurur ya da kayıtları
    # kırpardı. Daha geniş sütun eski kodla sorunsuz çalışır; hareket geçmişi kaybolmaz.
    op.drop_column("malzemeler", "lot_takipli")
    op.drop_table("sayim_satirlari")
    op.drop_table("sayim_oturumlari")
    op.drop_index(op.f("ix_stok_bakiyeleri_lokasyon_id"), table_name="stok_bakiyeleri")
    op.drop_table("stok_bakiyeleri")
    op.drop_index(op.f("ix_lokasyonlar_depo_id"), table_name="lokasyonlar")
    op.drop_table("lokasyonlar")
    op.drop_table("depolar")
