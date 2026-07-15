"""Ürün & Reçete modelleri (tenant şeması).

- ``Urun`` — üretilen mamul kartı (iş emrine bağlanır).
- ``Recete`` — ürün başına **tek** reçete (UNIQUE ``urun_id``; sürümleme Faz 6+).
- ``ReceteKalemi`` — reçetenin malzeme satırı (birim üretim başına miktar).

İş emri kapanışında BOM patlatma: ``recete_kalemleri.miktar × is_emri.miktar`` kadar
stok çıkışı üretilir (``urun.service.bom_patlat`` — idempotent). FK'ler şema önekiyle
yazılmaz; ``search_path`` çözer.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin


class Urun(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Üretilen mamul kartı."""

    __tablename__ = "urunler"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    birim: Mapped[str] = mapped_column(String(20), default="adet", nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    recete: Mapped[Recete | None] = relationship(back_populates="urun", uselist=False)


class Recete(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Ürün reçetesi (BOM başlığı) — ürün başına tek kayıt."""

    __tablename__ = "receteler"

    urun_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("urunler.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    ad: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    urun: Mapped[Urun] = relationship(back_populates="recete")
    kalemler: Mapped[list[ReceteKalemi]] = relationship(
        back_populates="recete", cascade="all, delete-orphan", order_by="ReceteKalemi.id"
    )


class ReceteKalemi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Reçete malzeme satırı (birim üretim başına tüketim)."""

    __tablename__ = "recete_kalemleri"
    __table_args__ = (UniqueConstraint("recete_id", "malzeme_id"),)

    recete_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("receteler.id", ondelete="CASCADE"), index=True, nullable=False
    )
    malzeme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("malzemeler.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    miktar: Mapped[Decimal] = mapped_column(Numeric(18, 3), nullable=False)

    recete: Mapped[Recete] = relationship(back_populates="kalemler")
