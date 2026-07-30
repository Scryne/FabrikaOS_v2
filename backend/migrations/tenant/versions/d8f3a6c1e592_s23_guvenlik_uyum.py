"""S23 güvenlik & uyum (ADR-0022): kullanıcıya TOTP 2FA kolonları + kurtarma kodları +
oturum kayıtları + KVKK ihraçları + consent kayıtları + denetim_izi append-only koruması.

Revision ID: d8f3a6c1e592
Revises: c4a7f3e9b528
Create Date: 2026-07-15 18:05:00.000000

Tenant şemasında; fan-out döngüsünde her aktif tenant şemasında çalışır. Trigger
fonksiyonu şema-yerel oluşturulur (``search_path`` migration bağlamından gelir).

``denetim_izi`` koruması: DELETE her zaman yasak; UPDATE yalnız kişisel veri maskesi
(kullanici_id / kullanici_eposta / ip_adresi) için serbest — adli çekirdek
(eylem, kaynak, kaynak_id, request_id, detay, olusturma_tarihi) değiştirilemez.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d8f3a6c1e592"
down_revision: str | None = "c4a7f3e9b528"
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
    # --- kullanici: TOTP 2FA ---
    op.add_column("kullanici", sa.Column("totp_sirri", sa.String(length=64), nullable=True))
    op.add_column(
        "kullanici",
        sa.Column(
            "iki_asama_aktif", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )

    # --- kurtarma_kodlari ---
    op.create_table(
        "kurtarma_kodlari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kullanici_id", sa.BigInteger(), nullable=False),
        sa.Column("kod_ozet", sa.String(length=64), nullable=False),
        sa.Column("kullanildi", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_kurtarma_kodlari_kullanici_id_kullanici"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kurtarma_kodlari")),
    )
    op.create_index(
        op.f("ix_kurtarma_kodlari_kullanici_id"), "kurtarma_kodlari", ["kullanici_id"]
    )

    # --- oturumlar ---
    op.create_table(
        "oturumlar",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kullanici_id", sa.BigInteger(), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("ip_adresi", sa.String(length=64), nullable=True),
        sa.Column("istemci", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("son_kullanim", sa.DateTime(timezone=True), nullable=True),
        sa.Column("bitis", sa.DateTime(timezone=True), nullable=False),
        sa.Column("iptal", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_oturumlar_kullanici_id_kullanici"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oturumlar")),
    )
    op.create_index(op.f("ix_oturumlar_kullanici_id"), "oturumlar", ["kullanici_id"])
    op.create_index(op.f("ix_oturumlar_jti"), "oturumlar", ["jti"], unique=True)

    # --- kvkk_ihraclari ---
    op.create_table(
        "kvkk_ihraclari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kod", sa.String(length=50), nullable=False),
        sa.Column("kisi_turu", sa.String(length=20), nullable=False),
        sa.Column("kisi_id", sa.BigInteger(), nullable=False),
        sa.Column("durum", sa.String(length=20), nullable=False, server_default="kuyrukta"),
        sa.Column("nesne_anahtari", sa.String(length=500), nullable=False, server_default=""),
        sa.Column("dosya_adi", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("boyut", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("kayit_sayisi", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("hata", sa.String(length=1000), nullable=False, server_default=""),
        sa.Column("olusturan_kullanici_id", sa.BigInteger(), nullable=True),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["olusturan_kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_kvkk_ihraclari_olusturan_kullanici_id_kullanici"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_kvkk_ihraclari")),
    )
    op.create_index(op.f("ix_kvkk_ihraclari_kod"), "kvkk_ihraclari", ["kod"], unique=True)
    op.create_index(op.f("ix_kvkk_ihraclari_kisi_id"), "kvkk_ihraclari", ["kisi_id"])
    op.create_index(op.f("ix_kvkk_ihraclari_durum"), "kvkk_ihraclari", ["durum"])
    op.create_index(
        op.f("ix_kvkk_ihraclari_olusturan_kullanici_id"),
        "kvkk_ihraclari",
        ["olusturan_kullanici_id"],
    )

    # --- consent_kayitlari ---
    op.create_table(
        "consent_kayitlari",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("kullanici_id", sa.BigInteger(), nullable=False),
        sa.Column("tur", sa.String(length=20), nullable=False),
        sa.Column("metin_surumu", sa.String(length=20), nullable=False),
        sa.Column("kabul", sa.Boolean(), nullable=False),
        sa.Column("ip_adresi", sa.String(length=64), nullable=True),
        *_zaman_damgalari(),
        sa.ForeignKeyConstraint(
            ["kullanici_id"],
            ["kullanici.id"],
            name=op.f("fk_consent_kayitlari_kullanici_id_kullanici"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consent_kayitlari")),
    )
    op.create_index(
        op.f("ix_consent_kayitlari_kullanici_id"), "consent_kayitlari", ["kullanici_id"]
    )

    # --- denetim_izi append-only koruması ---
    op.execute(
        """
        CREATE FUNCTION denetim_izi_koru() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'denetim_izi append-only: DELETE yasak';
          END IF;
          IF (NEW.eylem, NEW.kaynak, NEW.kaynak_id, NEW.request_id, NEW.detay,
              NEW.olusturma_tarihi)
             IS DISTINCT FROM
             (OLD.eylem, OLD.kaynak, OLD.kaynak_id, OLD.request_id, OLD.detay,
              OLD.olusturma_tarihi) THEN
            RAISE EXCEPTION
              'denetim_izi append-only: yalniz kisisel veri maskesi guncellenebilir';
          END IF;
          RETURN NEW;
        END $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER denetim_izi_koru_tg
        BEFORE UPDATE OR DELETE ON denetim_izi
        FOR EACH ROW EXECUTE FUNCTION denetim_izi_koru();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS denetim_izi_koru_tg ON denetim_izi")
    op.execute("DROP FUNCTION IF EXISTS denetim_izi_koru()")

    op.drop_index(op.f("ix_consent_kayitlari_kullanici_id"), table_name="consent_kayitlari")
    op.drop_table("consent_kayitlari")

    op.drop_index(
        op.f("ix_kvkk_ihraclari_olusturan_kullanici_id"), table_name="kvkk_ihraclari"
    )
    op.drop_index(op.f("ix_kvkk_ihraclari_durum"), table_name="kvkk_ihraclari")
    op.drop_index(op.f("ix_kvkk_ihraclari_kisi_id"), table_name="kvkk_ihraclari")
    op.drop_index(op.f("ix_kvkk_ihraclari_kod"), table_name="kvkk_ihraclari")
    op.drop_table("kvkk_ihraclari")

    op.drop_index(op.f("ix_oturumlar_jti"), table_name="oturumlar")
    op.drop_index(op.f("ix_oturumlar_kullanici_id"), table_name="oturumlar")
    op.drop_table("oturumlar")

    op.drop_index(op.f("ix_kurtarma_kodlari_kullanici_id"), table_name="kurtarma_kodlari")
    op.drop_table("kurtarma_kodlari")

    op.drop_column("kullanici", "iki_asama_aktif")
    op.drop_column("kullanici", "totp_sirri")
