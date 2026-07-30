"""KVKK ihraç artefaktına saklama süresi + indirme sayacı (ADR-0022 sertleştirmesi).

Revision ID: e5b1c7d4a238
Revises: d8f3a6c1e592
Create Date: 2026-07-30 15:40:00.000000

Hazır bir ihraç, kişinin TÜM modüllerdeki kişisel verisinin dökümüdür; süresiz
saklanması veri minimizasyonuna aykırıdır ve sızıntı yüzeyini büyütür.
``gecerlilik_bitisi`` dolduğunda artefakt nesne deposundan silinir, kayıt satırı
denetim için kalır (durum ``suresi_doldu``).

**Geriye dönük veri:** bu migration'dan önce üretilmiş "hazir" kayıtların bitiş damgası
yoktur. NULL bırakılsaydı süresiz erişilebilir kalırlardı; bu yüzden mevcut hazır
kayıtlara üretim (oluşturma) anından itibaren saklama penceresi **backfill** edilir.
Süresi zaten geçmiş olanlar bir sonraki indirme denemesinde ya da temizleme
taramasında silinir.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5b1c7d4a238"
down_revision: str | None = "d8f3a6c1e592"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SAKLAMA_GUN = 7


def upgrade() -> None:
    op.add_column(
        "kvkk_ihraclari",
        sa.Column("gecerlilik_bitisi", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "kvkk_ihraclari",
        sa.Column("indirme_sayisi", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.create_index(
        "ix_kvkk_ihraclari_gecerlilik_bitisi", "kvkk_ihraclari", ["gecerlilik_bitisi"]
    )

    # Backfill: mevcut hazır artefaktlara oluşturma anından itibaren pencere ver.
    op.execute(
        sa.text(
            "UPDATE kvkk_ihraclari "
            f"SET gecerlilik_bitisi = olusturma_tarihi + interval '{SAKLAMA_GUN} days' "
            "WHERE durum = 'hazir' AND gecerlilik_bitisi IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_index("ix_kvkk_ihraclari_gecerlilik_bitisi", table_name="kvkk_ihraclari")
    op.drop_column("kvkk_ihraclari", "indirme_sayisi")
    op.drop_column("kvkk_ihraclari", "gecerlilik_bitisi")
