"""Stok & Satınalma modelleri (tenant şeması).

- ``Malzeme`` — stok kartı; ``mevcut_miktar`` **tutulan bakiyedir** (her ``StokHareketi``
  servis katmanında ``FOR UPDATE`` ile günceller). ``kritik_stok`` kenar-tetikli
  ``stok.kritik`` olayının eşiğidir.
- ``StokHareketi`` — append-only hareket; ``bakiye_sonrasi`` o andaki bakiye snapshot'ı.
  ``idempotency_anahtari`` opsiyonel tekil — çift-gönderimi engeller.
- ``SatinalmaTalebi`` + ``SatinalmaTalebiKalemi`` — çok-kalemli talep; durum ``talep_durum.py``
  makinesiyle yönetilir.

FK'ler şema önekiyle yazılmaz (``malzemeler.id``, ``kullanici.id``); aktif ``search_path`` çözer.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin
from app.modules.stok.talep_durum import ILK_DURUM

_MIKTAR = Numeric(18, 3)
_PARA = Numeric(18, 2)


class Malzeme(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Stok kartı — tutulan bakiye + min/max/kritik eşikler."""

    __tablename__ = "malzemeler"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    birim: Mapped[str] = mapped_column(String(20), nullable=False)
    kategori: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    mevcut_miktar: Mapped[Decimal] = mapped_column(_MIKTAR, default=Decimal(0), nullable=False)
    min_stok: Mapped[Decimal] = mapped_column(_MIKTAR, default=Decimal(0), nullable=False)
    max_stok: Mapped[Decimal | None] = mapped_column(_MIKTAR, nullable=True)
    kritik_stok: Mapped[Decimal] = mapped_column(_MIKTAR, default=Decimal(0), nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Ana tedarikçi (S-VB): tedarikçi performans skorunun kalite bileşeni + S25 PO hazırlığı.
    tedarikci_firma_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("firmalar.id", ondelete="SET NULL"), index=True, nullable=True
    )


class StokHareketi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Stok hareketi (append-only) — bakiyeyi güncelleyen kayıt."""

    __tablename__ = "stok_hareketleri"

    malzeme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("malzemeler.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    tur: Mapped[str] = mapped_column(String(10), nullable=False)
    miktar: Mapped[Decimal] = mapped_column(_MIKTAR, nullable=False)
    bakiye_sonrasi: Mapped[Decimal] = mapped_column(_MIKTAR, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    kaynak: Mapped[str | None] = mapped_column(String(50), nullable=True)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    idempotency_anahtari: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, nullable=True
    )


class SatinalmaTalebi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Çok-kalemli satınalma talebi — yaşam döngüsü ``talep_durum.py``."""

    __tablename__ = "satinalma_talepleri"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    baslik: Mapped[str] = mapped_column(String(200), nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default=ILK_DURUM, index=True, nullable=False)
    para_birimi: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)
    talep_eden_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    onaylayan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    onay_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    red_nedeni: Mapped[str | None] = mapped_column(String(500), nullable=True)

    kalemler: Mapped[list[SatinalmaTalebiKalemi]] = relationship(
        back_populates="talep",
        cascade="all, delete-orphan",
        order_by="SatinalmaTalebiKalemi.id",
    )


class SatinalmaTalebiKalemi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Satınalma talebi kalemi (n–1 talep)."""

    __tablename__ = "satinalma_talebi_kalemleri"

    talep_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("satinalma_talepleri.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    malzeme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("malzemeler.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    miktar: Mapped[Decimal] = mapped_column(_MIKTAR, nullable=False)
    birim: Mapped[str] = mapped_column(String(20), nullable=False)
    tahmini_birim_fiyat: Mapped[Decimal | None] = mapped_column(_PARA, nullable=True)
    aciklama: Mapped[str] = mapped_column(String(500), default="", nullable=False)

    talep: Mapped[SatinalmaTalebi] = relationship(back_populates="kalemler")
