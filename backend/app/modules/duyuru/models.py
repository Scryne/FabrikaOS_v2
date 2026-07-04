"""Duyuru modülü modeli (tenant şeması).

``Duyuru`` — kurumsal duyuru. ``yayinda`` yayına alındığında ``duyuru.yeni`` gerçek-zaman
olayı üretilir (bağlı istemciler bildirim alır). ``hedef_departman`` boşsa tüm departmanlar.
FK'ler şema önekiyle yazılmaz; ``search_path`` çözer.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin


class Duyuru(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Kurumsal duyuru (yayınlanınca ``duyuru.yeni`` gerçek-zaman olayı)."""

    __tablename__ = "duyurular"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    baslik: Mapped[str] = mapped_column(String(200), nullable=False)
    icerik: Mapped[str] = mapped_column(String(5000), default="", nullable=False)
    onem: Mapped[str] = mapped_column(String(20), default="bilgi", index=True, nullable=False)
    yayinda: Mapped[bool] = mapped_column(Boolean, default=False, index=True, nullable=False)
    yayin_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    bitis_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hedef_departman: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
