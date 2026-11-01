"""Finans modelleri (tenant şeması, S29 / ADR-0048).

- ``CariHesap`` — firma başına bir tane (firma ilk hareketinde açılır). ``bakiye`` tutulan
  değerdir ve yalnız ``FOR UPDATE`` kilidi altında değişir; işaret: pozitif = firma bize borçlu.
- ``CariHareket`` — bakiyeyi değiştiren her olayın değiştirilemez kaydı (``bakiye_sonrasi`` ile
  ekstre). ``kaynak`` tekildir: aynı fatura/ödeme iki kez işlenmez (çift sayım yok).
- ``Fatura`` + ``FaturaKalemi`` — satış/alış faturası; toplamlar kalemlerden hesaplanıp saklanır.
  e-Fatura alanları (``ettn``, ``senaryo``, ``gib_durumu``) entegratör için iskelettir.
- ``Odeme`` — tahsilat (firmadan gelen) ya da ödeme (firmaya giden); isteğe bağlı faturaya bağlı.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin
from app.modules.finans.durum import ILK_DURUM

_PARA = Numeric(18, 2)


class CariHesap(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "cari_hesaplar"

    firma_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("firmalar.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    para_birimi: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)
    bakiye: Mapped[Decimal] = mapped_column(_PARA, default=Decimal("0.00"), nullable=False)


class CariHareket(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "cari_hareketler"

    cari_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("cari_hesaplar.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # fatura_satis | fatura_alis | tahsilat | odeme | fatura_iptal
    tur: Mapped[str] = mapped_column(String(20), nullable=False)
    tutar: Mapped[Decimal] = mapped_column(_PARA, nullable=False)  # işaretli bakiye etkisi
    bakiye_sonrasi: Mapped[Decimal] = mapped_column(_PARA, nullable=False)
    tarih: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    # "fatura:12", "fatura-iptal:12", "odeme:7" — tekil: aynı olay ikinci kez bakiyeye girmez.
    kaynak: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )


class Fatura(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "faturalar"
    __table_args__ = (
        CheckConstraint("odenen_tutar >= 0", name="ck_faturalar_odenen"),
        CheckConstraint("odenen_tutar <= genel_toplam", name="ck_faturalar_odenen_ust"),
    )

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    tur: Mapped[str] = mapped_column(String(10), index=True, nullable=False)  # satis | alis
    firma_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("firmalar.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    durum: Mapped[str] = mapped_column(String(20), default=ILK_DURUM, index=True, nullable=False)
    fatura_tarihi: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    vade_tarihi: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    para_birimi: Mapped[str] = mapped_column(String(3), default="TRY", nullable=False)
    ara_toplam: Mapped[Decimal] = mapped_column(_PARA, default=Decimal("0.00"), nullable=False)
    kdv_toplam: Mapped[Decimal] = mapped_column(_PARA, default=Decimal("0.00"), nullable=False)
    genel_toplam: Mapped[Decimal] = mapped_column(_PARA, default=Decimal("0.00"), nullable=False)
    odenen_tutar: Mapped[Decimal] = mapped_column(_PARA, default=Decimal("0.00"), nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    iade_nedeni: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    iptal_nedeni: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    # Kaynak belge (isteğe bağlı): alış faturası satınalma siparişinden gelebilir.
    satinalma_siparisi_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("satinalma_siparisleri.id", ondelete="SET NULL"), nullable=True
    )
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    kesen_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )
    kesim_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # e-Fatura iskeleti (entegratör GİB'e iletir; ürün yalnız alanları ve durumu tutar).
    ettn: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    senaryo: Mapped[str] = mapped_column(String(20), default="TEMELFATURA", nullable=False)
    gib_durumu: Mapped[str] = mapped_column(String(20), default="gonderilmedi", nullable=False)

    kalemler: Mapped[list[FaturaKalemi]] = relationship(
        back_populates="fatura",
        cascade="all, delete-orphan",
        order_by="FaturaKalemi.sira",
        lazy="selectin",
    )


class FaturaKalemi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "fatura_kalemleri"
    __table_args__ = (CheckConstraint("miktar > 0", name="ck_fatura_kalemleri_miktar"),)

    fatura_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("faturalar.id", ondelete="CASCADE"), index=True, nullable=False
    )
    sira: Mapped[int] = mapped_column(Integer, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(300), nullable=False)
    malzeme_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("malzemeler.id", ondelete="SET NULL"), nullable=True
    )
    miktar: Mapped[Decimal] = mapped_column(Numeric(14, 3), nullable=False)
    birim: Mapped[str] = mapped_column(String(20), default="adet", nullable=False)
    birim_fiyat: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    kdv_orani: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    satir_tutari: Mapped[Decimal] = mapped_column(_PARA, nullable=False)
    kdv_tutari: Mapped[Decimal] = mapped_column(_PARA, nullable=False)

    fatura: Mapped[Fatura] = relationship(back_populates="kalemler")


class Odeme(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "odemeler"
    __table_args__ = (CheckConstraint("tutar > 0", name="ck_odemeler_tutar"),)

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    tur: Mapped[str] = mapped_column(String(10), index=True, nullable=False)  # tahsilat | odeme
    firma_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("firmalar.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    fatura_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("faturalar.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    tarih: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    tutar: Mapped[Decimal] = mapped_column(_PARA, nullable=False)
    yontem: Mapped[str] = mapped_column(String(20), default="havale", nullable=False)
    aciklama: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    # İstemci yeniden denemesinde aynı ödeme iki kez kaydedilmez (ağ kopması, çift tık).
    idempotency_anahtari: Mapped[str | None] = mapped_column(String(80), unique=True, nullable=True)
    kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )
