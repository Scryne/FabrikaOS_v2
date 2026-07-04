"""Sözleşme modülü modeli (tenant şeması).

``Sozlesme`` — firmaya bağlı sözleşme; yaşam döngüsü ``durum`` makinesiyle. ``bitis_tarihi``
yaklaşınca (``yaklasim_bildirildi`` kenar-tetikli bayrağı ile bir kez) ``sozlesme.yaklasiyor``
domain olayı üretilir. FK'ler şema önekiyle yazılmaz; ``search_path`` çözer.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin
from app.modules.sozlesme.durum import ILK_DURUM


class Sozlesme(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Cari sözleşme — yaşam döngüsü ``sozlesme.durum`` makinesiyle."""

    __tablename__ = "sozlesmeler"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    firma_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("firmalar.id"), index=True, nullable=False
    )
    baslik: Mapped[str] = mapped_column(String(200), nullable=False)
    tur: Mapped[str] = mapped_column(String(20), default="hizmet", nullable=False)
    baslangic_tarihi: Mapped[date] = mapped_column(Date, nullable=False)
    bitis_tarihi: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    tutar: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    para_birimi: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default=ILK_DURUM, index=True, nullable=False)
    sorumlu_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # Kenar-tetikli: yaklaşan-bitiş olayı sözleşme başına yalnız bir kez üretilir.
    yaklasim_bildirildi: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
