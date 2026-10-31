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

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
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
    # S25 (ADR-0024 §4): açıksa giriş hareketleri lot numarası ister; kapalıysa lot ''.
    lot_takipli: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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
    tur: Mapped[str] = mapped_column(String(20), nullable=False)
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
    # S25: hareketin lokasyonu ve lotu; transferin iki bacağı aynı ``transfer_grubu``nu taşır.
    lokasyon_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("lokasyonlar.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    lot_no: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    transfer_grubu: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)


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


class Depo(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Depo (S25) — lokasyonların kökü."""

    __tablename__ = "depolar"

    kod: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(120), nullable=False)
    adres: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Lokasyon(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Depo içi lokasyon (raf/göz/alan); ``ust_lokasyon_id`` ile hiyerarşi."""

    __tablename__ = "lokasyonlar"
    __table_args__ = (UniqueConstraint("depo_id", "kod", name="uq_lokasyonlar_depo_id"),)

    depo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("depolar.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    ust_lokasyon_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("lokasyonlar.id", ondelete="RESTRICT"), nullable=True
    )
    kod: Mapped[str] = mapped_column(String(40), nullable=False)
    ad: Mapped[str] = mapped_column(String(120), nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class StokBakiyesi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Lokasyon × lot bakiyesi (ADR-0024 §2/§4). Malzeme toplamı ``Malzeme.mevcut_miktar``."""

    __tablename__ = "stok_bakiyeleri"
    __table_args__ = (
        UniqueConstraint(
            "malzeme_id", "lokasyon_id", "lot_no", name="uq_stok_bakiyeleri_malzeme_id"
        ),
        CheckConstraint("miktar >= 0", name="ck_stok_bakiyeleri_negatif_degil"),
    )

    malzeme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("malzemeler.id", ondelete="RESTRICT"), nullable=False
    )
    lokasyon_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lokasyonlar.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    lot_no: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    miktar: Mapped[Decimal] = mapped_column(_MIKTAR, default=Decimal(0), nullable=False)


class SayimOturumu(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Bir lokasyonun sayımı: acik → onay_bekliyor → onaylandi | iptal (ADR-0024 §1)."""

    __tablename__ = "sayim_oturumlari"

    kod: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    lokasyon_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lokasyonlar.id", ondelete="RESTRICT"), nullable=False
    )
    durum: Mapped[str] = mapped_column(String(20), default="acik", nullable=False)
    aciklama: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )
    onaylayan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )
    onay_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    satirlar: Mapped[list[SayimSatiri]] = relationship(
        back_populates="oturum", cascade="all, delete-orphan", order_by="SayimSatiri.id"
    )


class SayimSatiri(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Sayım satırı. ``sistem_miktari`` satır açıldığı andaki bakiyedir; onayda fark DELTA
    olarak uygulanır, aradaki hareketler korunur (ADR-0024 §1)."""

    __tablename__ = "sayim_satirlari"
    __table_args__ = (
        UniqueConstraint("oturum_id", "malzeme_id", "lot_no", name="uq_sayim_satirlari_oturum_id"),
        CheckConstraint("sayilan_miktar >= 0", name="ck_sayim_satirlari_sayilan"),
    )

    oturum_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("sayim_oturumlari.id", ondelete="CASCADE"), nullable=False
    )
    malzeme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("malzemeler.id", ondelete="RESTRICT"), nullable=False
    )
    lot_no: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    sistem_miktari: Mapped[Decimal] = mapped_column(_MIKTAR, nullable=False)
    sayilan_miktar: Mapped[Decimal] = mapped_column(_MIKTAR, nullable=False)
    uygulanan_hareket_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stok_hareketleri.id", ondelete="SET NULL"), nullable=True
    )

    oturum: Mapped[SayimOturumu] = relationship(back_populates="satirlar")

    @property
    def fark(self) -> Decimal:
        return self.sayilan_miktar - self.sistem_miktari
