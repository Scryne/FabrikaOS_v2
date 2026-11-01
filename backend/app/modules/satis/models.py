"""Satış modeli (tenant şeması, S31 / ADR-0050).

- ``SatisSiparisi`` — müşteri siparişi (oto kod ``SP-``, CRM firması). İsteğe bağlı olarak bir dış
  portal talebinden doğar (``talep_id`` tekil: bir talep tek siparişe dönüşür).
- ``SatisSiparisiKalemi`` — ürün × miktar (reçete MRP'de patlatılır).
- ``MrpTetigi`` — onayın açtığı iş emri / satınalma talebi kaydı. ``kaynak`` tekildir
  (``ie:<kalem_id>``, ``st:<siparis_id>``): aynı tetik ikinci kez yazılamaz → çift üretim yok.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin
from app.modules.satis.durum import ILK_DURUM

_MIKTAR = Numeric(18, 3)
_PARA = Numeric(18, 4)


class SatisSiparisi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "satis_siparisleri"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    firma_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("firmalar.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    talep_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("talepler.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    # Üretim emirlerinin açılacağı makine (sipariş başına bir hat; boşsa onayda verilir).
    makine_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="SET NULL"), nullable=True
    )
    durum: Mapped[str] = mapped_column(String(20), default=ILK_DURUM, index=True, nullable=False)
    teslim_tarihi: Mapped[date] = mapped_column(Date, nullable=False)
    para_birimi: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )
    onaylayan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )

    kalemler: Mapped[list[SatisSiparisiKalemi]] = relationship(
        cascade="all, delete-orphan", order_by="SatisSiparisiKalemi.sira", lazy="selectin"
    )


class SatisSiparisiKalemi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "satis_siparisi_kalemleri"
    __table_args__ = (CheckConstraint("miktar > 0", name="miktar"),)

    siparis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("satis_siparisleri.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sira: Mapped[int] = mapped_column(Integer, nullable=False)
    urun_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("urunler.id", ondelete="RESTRICT"), nullable=False
    )
    miktar: Mapped[Decimal] = mapped_column(_MIKTAR, nullable=False)
    birim_fiyat: Mapped[Decimal | None] = mapped_column(_PARA, nullable=True)


class MrpTetigi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "mrp_tetikleri"

    siparis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("satis_siparisleri.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kaynak: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    tur: Mapped[str] = mapped_column(String(20), nullable=False)  # is_emri | satinalma_talebi
    hedef_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
