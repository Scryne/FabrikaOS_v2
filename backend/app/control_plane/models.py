"""Control-plane modelleri (public şema): ``Tenant`` ve ``Abonelik``.

``Tenant.slug`` aynı zamanda şema adının (``tenant_<slug>``) kaynağıdır; bu yüzden
katı bir biçim (küçük harf, rakam, tire) zorunludur — bkz. ``tenancy.SLUG_DESENI``.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import KimlikMixin, PublicBase, ZamanDamgaliMixin

# Abonelik durumları — geçerli sayılanlar erişime izin verir.
ABONELIK_GECERLI_DURUMLAR = frozenset({"deneme", "aktif"})


class Tenant(KimlikMixin, ZamanDamgaliMixin, PublicBase):
    """Bir fabrika/kiracı. Her tenant'ın izole bir ``tenant_<slug>`` şeması vardır."""

    __tablename__ = "tenant"

    slug: Mapped[str] = mapped_column(String(63), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    abonelikler: Mapped[list[Abonelik]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def abonelik_gecerli(self) -> bool:
        """Geçerli (deneme/aktif ve süresi geçmemiş) bir abonelik var mı?

        Not: ``abonelikler`` ilişkisinin önceden yüklenmiş olması gerekir (eager load).
        """
        simdi = datetime.now(UTC)
        for ab in self.abonelikler:
            if ab.durum not in ABONELIK_GECERLI_DURUMLAR:
                continue
            if ab.bitis_tarihi is not None and ab.bitis_tarihi < simdi:
                continue
            return True
        return False


class Abonelik(KimlikMixin, ZamanDamgaliMixin, PublicBase):
    """Bir tenant'ın plan/abonelik kaydı (control-plane)."""

    __tablename__ = "abonelik"

    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenant.id", ondelete="CASCADE"), index=True, nullable=False
    )
    plan_kodu: Mapped[str] = mapped_column(String(50), default="deneme", nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default="deneme", nullable=False)
    baslangic_tarihi: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bitis_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tenant: Mapped[Tenant] = relationship(back_populates="abonelikler")
