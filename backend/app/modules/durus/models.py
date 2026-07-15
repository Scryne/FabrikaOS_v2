"""Duruş yönetimi modelleri (tenant şeması).

- ``DurusNedeni`` — planlı/plansız sınıflı neden kataloğu (pareto kırılımının anahtarı).
- ``DurusKaydi`` — makine + kapalı zaman aralığı + neden. Kayıtlı duruş dakikaları OEE
  kullanılabilirlik hesabına **eklenir** (üretim verisindeki ``durus_sure_dk``'ya ek
  bağımsız kaynak; bkz. ``uretim.service``).

FK'ler şema önekiyle yazılmaz; ``search_path`` çözer (tenant-rbac-conventions).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

# Duruş sınıfları (pareto + planlı bakım ayrımı).
DURUS_SINIFLARI = frozenset({"planli", "plansiz"})


class DurusNedeni(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Duruş nedeni kataloğu."""

    __tablename__ = "durus_nedenleri"

    ad: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    sinif: Mapped[str] = mapped_column(String(10), default="plansiz", nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DurusKaydi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Makine duruş kaydı (kapalı aralık: başlangıç < bitiş)."""

    __tablename__ = "durus_kayitlari"

    makine_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="CASCADE"), index=True, nullable=False
    )
    neden_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("durus_nedenleri.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    baslangic: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    bitis: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    aciklama: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )

    @property
    def sure_dk(self) -> float:
        return (self.bitis - self.baslangic).total_seconds() / 60.0
