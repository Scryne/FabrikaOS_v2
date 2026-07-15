"""Bakım modülü modelleri (tenant şeması).

- ``BakimPlani`` — makineye n–1 bağlı bakım planı (önleyici/kestirimci/periyodik).
  S24: vade taraması (``POST /bakim-planlari/vade-tara``) vadesi gelen plandan otomatik
  iş emri üretir (``is_emirleri.bakim_plani_id`` bağlantısı bir-kez dedup'ıdır);
  ``yedek_parca_malzeme_id`` yedek parça = malzeme ilişkisidir.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

# Bakım planı türleri.
BAKIM_TIPLERI = frozenset({"onleyici", "kestirimci", "periyodik"})


class BakimPlani(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Makineye bağlı bakım planı."""

    __tablename__ = "bakim_planlari"

    makine_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    tip: Mapped[str] = mapped_column(String(20), default="onleyici", nullable=False)
    periyot_gun: Mapped[int | None] = mapped_column(Integer, nullable=True)
    son_bakim_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sonraki_bakim_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    # Yedek parça = malzeme ilişkisi (S24): bakımda kullanılan ana yedek parça kartı.
    yedek_parca_malzeme_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("malzemeler.id", ondelete="SET NULL"), nullable=True
    )
