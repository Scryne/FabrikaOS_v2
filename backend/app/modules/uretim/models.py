"""Üretim modülü modelleri (tenant şeması).

- ``Makine`` — normal tablo.
- ``UretimVerisi`` — TimescaleDB **hypertable** (yüksek hacimli zaman serisi). Partition
  kolonu ``zaman``; hypertable kuralı gereği birincil anahtar bu kolonu içerir → ``(zaman, id)``.
- ``ArizaKaydi`` — normal tablo (düşük hacim).

Hypertable'a dönüştürme (``create_hypertable``) migration adımındadır; fan-out döngüsünde
her tenant şemasında çalışır (bkz. ADR-0006 / alembic-fan-out).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

# Makine durumları.
MAKINE_DURUMLARI = frozenset({"calisiyor", "durdu", "bakimda", "ariza"})


class Makine(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Üretim makinesi."""

    __tablename__ = "makineler"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default="durdu", nullable=False)
    oee_hedefi: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Coğrafi site haritası (S-VB): koordinatsız makine yalnız SVG şemada görünür.
    enlem: Mapped[float | None] = mapped_column(Float, nullable=True)
    boylam: Mapped[float | None] = mapped_column(Float, nullable=True)

    uretim_verileri: Mapped[list[UretimVerisi]] = relationship(
        back_populates="makine", cascade="all, delete-orphan"
    )
    arizalar: Mapped[list[ArizaKaydi]] = relationship(
        back_populates="makine", cascade="all, delete-orphan"
    )


class UretimVerisi(TenantBase):
    """Makine üretim ölçümü (zaman serisi / hypertable). OEE girdilerini taşır."""

    __tablename__ = "uretim_verileri"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), nullable=False)
    zaman: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    makine_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="CASCADE"), nullable=False
    )
    vardiya: Mapped[str | None] = mapped_column(String(20), nullable=True)
    planlanan_sure_dk: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    durus_sure_dk: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    toplam_adet: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    saglam_adet: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ideal_cevrim_sn: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # İzlenebilirlik (S24): üretilen lot/parti numarası (ileri izleme anahtarı).
    lot_no: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)

    makine: Mapped[Makine] = relationship(back_populates="uretim_verileri")

    __table_args__ = (
        # Hypertable partition kolonu (zaman) PK'ye dahil olmak zorunda.
        PrimaryKeyConstraint("zaman", "id", name="pk_uretim_verileri"),
        Index("ix_uretim_verileri_makine_zaman", "makine_id", "zaman"),
    )


class ArizaKaydi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Makine arıza/durış kaydı."""

    __tablename__ = "ariza_kayitlari"

    makine_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="CASCADE"), index=True, nullable=False
    )
    baslangic: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    bitis: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    tur: Mapped[str] = mapped_column(String(50), default="ariza", nullable=False)
    aciklama: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    cozuldu: Mapped[bool] = mapped_column(default=False, nullable=False)

    makine: Mapped[Makine] = relationship(back_populates="arizalar")
