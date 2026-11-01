"""S28 alan şifrelemesi: TOTP sırrı + webhook imza anahtarı (ADR-0047).

Revision ID: e6b8d0f2a4c6
Revises: d4f6b8a0c2e3
Create Date: 2026-11-01 05:00:00.000000

Tenant şemasında; fan-out döngüsünde her aktif tenant şemasında çalışır.

- ``kullanici.totp_sirri`` 64 → 255, ``webhook_abonelikleri.gizli_anahtar`` 120 → 255 karakter
  (Fernet belirteci ~140–200 karakter).
- Var olan düz metin sırlar uygulamanın anahtarıyla şifrelenir; geri almada çözülür. Göç
  uygulamanın ``SECRET_KEY`` / ``VERI_SIFRELEME_ANAHTARLARI`` ayarını okur: dağıtımda uygulamayla
  aynı ortamda koşmalıdır (``goc_dagit.py`` öyle koşar).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.core.security import sifreleme

revision: str = "e6b8d0f2a4c6"
down_revision: str | None = "d4f6b8a0c2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (tablo, sütun, eski uzunluk)
_ALANLAR = (("kullanici", "totp_sirri", 64), ("webhook_abonelikleri", "gizli_anahtar", 120))


def _donustur(tablo: str, sutun: str, donusum: str) -> None:
    baglanti = op.get_bind()
    satirlar = baglanti.execute(
        sa.text(f"SELECT id, {sutun} FROM {tablo} WHERE {sutun} IS NOT NULL")  # noqa: S608 — sabit liste
    ).fetchall()
    for kid, deger in satirlar:
        if donusum == "sifrele" and not deger.startswith(sifreleme.ONEK):
            yeni = sifreleme.sifrele(deger)
        elif donusum == "coz" and deger.startswith(sifreleme.ONEK):
            yeni = sifreleme.coz(deger)
        else:
            continue
        baglanti.execute(
            sa.text(f"UPDATE {tablo} SET {sutun} = :d WHERE id = :i"),  # noqa: S608
            {"d": yeni, "i": kid},
        )


def upgrade() -> None:
    for tablo, sutun, eski in _ALANLAR:
        op.alter_column(tablo, sutun, type_=sa.String(255), existing_type=sa.String(eski))
        _donustur(tablo, sutun, "sifrele")


def downgrade() -> None:
    for tablo, sutun, eski in _ALANLAR:
        _donustur(tablo, sutun, "coz")
        op.alter_column(tablo, sutun, type_=sa.String(eski), existing_type=sa.String(255))
