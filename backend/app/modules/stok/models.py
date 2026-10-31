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

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
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
    # S25-B (ADR-0024 §4b): PO'suz hızlı mal kabul; resmî teslim alma bunu eşleştirir.
    hizli_kabul: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


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


# ── S25-B: satınalma siparişi → teslim alma → iade (ADR-0024 §3, §4b) ─────────


class SatinalmaSiparisi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Onaylanmış talepten açılan sipariş: acik → kismi_teslim → tamamlandi | kapatildi | iptal."""

    __tablename__ = "satinalma_siparisleri"

    kod: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    talep_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("satinalma_talepleri.id", ondelete="RESTRICT"), nullable=False
    )
    tedarikci_firma_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("firmalar.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    durum: Mapped[str] = mapped_column(String(20), default="acik", index=True, nullable=False)
    para_birimi: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)
    beklenen_teslim_tarihi: Mapped[date | None] = mapped_column(Date, nullable=True)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )
    kapanis_nedeni: Mapped[str | None] = mapped_column(String(500), nullable=True)

    kalemler: Mapped[list[SatinalmaSiparisiKalemi]] = relationship(
        back_populates="siparis",
        cascade="all, delete-orphan",
        order_by="SatinalmaSiparisiKalemi.id",
    )


class SatinalmaSiparisiKalemi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Sipariş kalemi; ``teslim_alinan_miktar`` iadeler düşülmüş kümülatif teslimdir."""

    __tablename__ = "satinalma_siparisi_kalemleri"
    __table_args__ = (
        CheckConstraint("miktar > 0", name="ck_satinalma_siparisi_kalemleri_miktar"),
        CheckConstraint("teslim_alinan_miktar >= 0", name="ck_satinalma_siparisi_kalemleri_teslim"),
    )

    siparis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("satinalma_siparisleri.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    talep_kalemi_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("satinalma_talebi_kalemleri.id", ondelete="SET NULL"), nullable=True
    )
    malzeme_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("malzemeler.id", ondelete="RESTRICT"), nullable=False
    )
    miktar: Mapped[Decimal] = mapped_column(_MIKTAR, nullable=False)
    birim_fiyat: Mapped[Decimal | None] = mapped_column(_PARA, nullable=True)
    fazla_teslim_toleransi_yuzde: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), default=Decimal(0), nullable=False
    )
    teslim_alinan_miktar: Mapped[Decimal] = mapped_column(
        _MIKTAR, default=Decimal(0), nullable=False
    )

    siparis: Mapped[SatinalmaSiparisi] = relationship(back_populates="kalemler")


class TeslimAlma(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """İrsaliye başlığı. ``tur='iade'`` kayıt ``iade_edilen_id`` ile orijinal teslime bağlıdır."""

    __tablename__ = "teslim_almalar"
    __table_args__ = (
        UniqueConstraint("siparis_id", "irsaliye_no", "tur", name="uq_teslim_almalar_siparis_id"),
        CheckConstraint("tur IN ('teslim', 'iade')", name="ck_teslim_almalar_tur"),
    )

    siparis_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("satinalma_siparisleri.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    tur: Mapped[str] = mapped_column(String(10), default="teslim", nullable=False)
    irsaliye_no: Mapped[str] = mapped_column(String(40), nullable=False)
    iade_edilen_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("teslim_almalar.id", ondelete="RESTRICT"), nullable=True
    )
    # Fiziksel geliş anı (§4b): gelecekte ve sipariş tarihinden önce olamaz.
    fiili_tarih: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Beklenen teslim tarihi yoksa ``None`` (tedarikçi skoruna katılmaz).
    zamaninda: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    aciklama: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    idempotency_anahtari: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )

    kalemler: Mapped[list[TeslimAlmaKalemi]] = relationship(
        back_populates="teslim", cascade="all, delete-orphan", order_by="TeslimAlmaKalemi.id"
    )


class TeslimAlmaKalemi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Teslim/iade satırı. Hızlı mal kabulle eşleştiyse ``eslesen_hareket_id`` dolu,
    ``stok_hareketi_id`` boştur (çift sayım yok)."""

    __tablename__ = "teslim_alma_kalemleri"
    __table_args__ = (CheckConstraint("miktar > 0", name="ck_teslim_alma_kalemleri_miktar"),)

    teslim_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("teslim_almalar.id", ondelete="CASCADE"), index=True, nullable=False
    )
    siparis_kalemi_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("satinalma_siparisi_kalemleri.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    iade_edilen_kalem_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("teslim_alma_kalemleri.id", ondelete="RESTRICT"), nullable=True
    )
    miktar: Mapped[Decimal] = mapped_column(_MIKTAR, nullable=False)
    lokasyon_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("lokasyonlar.id", ondelete="RESTRICT"), nullable=False
    )
    lot_no: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    fazla_teslim: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    stok_hareketi_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("stok_hareketleri.id", ondelete="RESTRICT"), nullable=True
    )
    eslesen_hareket_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("stok_hareketleri.id", ondelete="RESTRICT"),
        unique=True,
        nullable=True,
    )

    teslim: Mapped[TeslimAlma] = relationship(back_populates="kalemler")
