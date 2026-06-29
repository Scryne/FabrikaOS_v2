"""isemri: is_emirleri + is_emri_yorumlari, bakim: bakim_planlari, outbox: giden_olaylar

Revision ID: c5a2f1b8e34d
Revises: 9e7a768e7184
Create Date: 2026-06-29 10:15:00.000000

Tüm tablolar tenant şemasındadır; fan-out döngüsünde (env.py) public + her aktif
tenant şemasında çalışır. Hypertable yoktur (hepsi normal tablo).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'c5a2f1b8e34d'
down_revision: str | None = '9e7a768e7184'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- is_emirleri ---
    op.create_table(
        'is_emirleri',
        sa.Column('kod', sa.String(length=50), nullable=False),
        sa.Column('baslik', sa.String(length=200), nullable=False),
        sa.Column('aciklama', sa.String(length=1000), nullable=False),
        sa.Column('makine_id', sa.BigInteger(), nullable=False),
        sa.Column('atanan_kullanici_id', sa.BigInteger(), nullable=True),
        sa.Column('durum', sa.String(length=20), nullable=False),
        sa.Column('oncelik', sa.String(length=10), nullable=False),
        sa.Column('kapanis_tarihi', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('guncelleme_tarihi', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['makine_id'], ['makineler.id'],
                                name=op.f('fk_is_emirleri_makine_id_makineler'),
                                ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['atanan_kullanici_id'], ['kullanici.id'],
                                name=op.f('fk_is_emirleri_atanan_kullanici_id_kullanici'),
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_is_emirleri')),
    )
    op.create_index(op.f('ix_is_emirleri_kod'), 'is_emirleri', ['kod'], unique=True)
    op.create_index(op.f('ix_is_emirleri_makine_id'), 'is_emirleri', ['makine_id'], unique=False)
    op.create_index(op.f('ix_is_emirleri_atanan_kullanici_id'), 'is_emirleri',
                    ['atanan_kullanici_id'], unique=False)
    op.create_index(op.f('ix_is_emirleri_durum'), 'is_emirleri', ['durum'], unique=False)

    # --- is_emri_yorumlari ---
    op.create_table(
        'is_emri_yorumlari',
        sa.Column('is_emri_id', sa.BigInteger(), nullable=False),
        sa.Column('yazan_kullanici_id', sa.BigInteger(), nullable=True),
        sa.Column('yazan_eposta', sa.String(length=255), nullable=True),
        sa.Column('metin', sa.String(length=2000), nullable=False),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('guncelleme_tarihi', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['is_emri_id'], ['is_emirleri.id'],
                                name=op.f('fk_is_emri_yorumlari_is_emri_id_is_emirleri'),
                                ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['yazan_kullanici_id'], ['kullanici.id'],
                                name=op.f('fk_is_emri_yorumlari_yazan_kullanici_id_kullanici'),
                                ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_is_emri_yorumlari')),
    )
    op.create_index(op.f('ix_is_emri_yorumlari_is_emri_id'), 'is_emri_yorumlari',
                    ['is_emri_id'], unique=False)
    op.create_index(op.f('ix_is_emri_yorumlari_yazan_kullanici_id'), 'is_emri_yorumlari',
                    ['yazan_kullanici_id'], unique=False)

    # --- bakim_planlari ---
    op.create_table(
        'bakim_planlari',
        sa.Column('makine_id', sa.BigInteger(), nullable=False),
        sa.Column('ad', sa.String(length=200), nullable=False),
        sa.Column('tip', sa.String(length=20), nullable=False),
        sa.Column('periyot_gun', sa.Integer(), nullable=True),
        sa.Column('son_bakim_tarihi', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sonraki_bakim_tarihi', sa.DateTime(timezone=True), nullable=True),
        sa.Column('aktif', sa.Boolean(), nullable=False),
        sa.Column('aciklama', sa.String(length=1000), nullable=False),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('guncelleme_tarihi', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['makine_id'], ['makineler.id'],
                                name=op.f('fk_bakim_planlari_makine_id_makineler'),
                                ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_bakim_planlari')),
    )
    op.create_index(op.f('ix_bakim_planlari_makine_id'), 'bakim_planlari',
                    ['makine_id'], unique=False)

    # --- giden_olaylar (transactional outbox) ---
    op.create_table(
        'giden_olaylar',
        sa.Column('dis_anahtar', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('olay_turu', sa.String(length=80), nullable=False),
        sa.Column('govde', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('durum', sa.String(length=20), nullable=False),
        sa.Column('deneme_sayisi', sa.Integer(), nullable=False),
        sa.Column('gonderim_tarihi', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('olusturma_tarihi', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('guncelleme_tarihi', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_giden_olaylar')),
    )
    op.create_index(op.f('ix_giden_olaylar_dis_anahtar'), 'giden_olaylar',
                    ['dis_anahtar'], unique=True)
    op.create_index(op.f('ix_giden_olaylar_olay_turu'), 'giden_olaylar',
                    ['olay_turu'], unique=False)
    op.create_index(op.f('ix_giden_olaylar_durum'), 'giden_olaylar', ['durum'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_giden_olaylar_durum'), table_name='giden_olaylar')
    op.drop_index(op.f('ix_giden_olaylar_olay_turu'), table_name='giden_olaylar')
    op.drop_index(op.f('ix_giden_olaylar_dis_anahtar'), table_name='giden_olaylar')
    op.drop_table('giden_olaylar')

    op.drop_index(op.f('ix_bakim_planlari_makine_id'), table_name='bakim_planlari')
    op.drop_table('bakim_planlari')

    op.drop_index(op.f('ix_is_emri_yorumlari_yazan_kullanici_id'), table_name='is_emri_yorumlari')
    op.drop_index(op.f('ix_is_emri_yorumlari_is_emri_id'), table_name='is_emri_yorumlari')
    op.drop_table('is_emri_yorumlari')

    op.drop_index(op.f('ix_is_emirleri_durum'), table_name='is_emirleri')
    op.drop_index(op.f('ix_is_emirleri_atanan_kullanici_id'), table_name='is_emirleri')
    op.drop_index(op.f('ix_is_emirleri_makine_id'), table_name='is_emirleri')
    op.drop_index(op.f('ix_is_emirleri_kod'), table_name='is_emirleri')
    op.drop_table('is_emirleri')
