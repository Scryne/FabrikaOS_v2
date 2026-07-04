"""İK modülü modelleri (tenant şeması) — personel özlük + izin/mesai/zimmet/sertifika.

- ``Personel`` — çalışan özlük kaydı. ``tc_kimlik_no`` KVKK kapsamında hassastır; API
  yanıtlarında **maskelenir** (yalnız son 2 hane). ``kullanici_id`` personeli bir giriş
  hesabına opsiyonel bağlar.
- ``IzinTalebi`` — izin talebi; yaşam döngüsü ``izin_durum`` makinesiyle; onay ``ik:onay`` ister.
- ``FazlaMesai`` / ``Zimmet`` / ``Sertifika`` — personele bağlı yardımcı özlük kayıtları.

FK'ler şema önekiyle yazılmaz (``personel.id``, ``kullanici.id``); ``search_path`` çözer.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin
from app.modules.ik.izin_durum import ILK_DURUM


class Personel(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Çalışan özlük kaydı (KVKK: ``tc_kimlik_no`` yanıtta maskelenir)."""

    __tablename__ = "personel"

    sicil_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(100), nullable=False)
    soyad: Mapped[str] = mapped_column(String(100), nullable=False)
    tc_kimlik_no: Mapped[str] = mapped_column(String(11), default="", nullable=False)
    dogum_tarihi: Mapped[date | None] = mapped_column(Date, nullable=True)
    telefon: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    eposta: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    departman: Mapped[str] = mapped_column(String(100), default="", index=True, nullable=False)
    unvan: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    ise_giris_tarihi: Mapped[date | None] = mapped_column(Date, nullable=True)
    yillik_izin_hakki: Mapped[int] = mapped_column(Integer, default=14, nullable=False)
    kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class IzinTalebi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """İzin talebi — yaşam döngüsü ``izin_durum``; onay ``ik:onay`` iznini gerektirir."""

    __tablename__ = "izin_talepleri"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    personel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("personel.id", ondelete="CASCADE"), index=True, nullable=False
    )
    izin_turu: Mapped[str] = mapped_column(String(20), default="yillik", nullable=False)
    baslangic_tarihi: Mapped[date] = mapped_column(Date, nullable=False)
    bitis_tarihi: Mapped[date] = mapped_column(Date, nullable=False)
    gun_sayisi: Mapped[int] = mapped_column(Integer, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default=ILK_DURUM, index=True, nullable=False)
    talep_eden_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    onaylayan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    onay_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    red_nedeni: Mapped[str] = mapped_column(String(1000), default="", nullable=False)


class FazlaMesai(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Personel fazla mesai kaydı."""

    __tablename__ = "fazla_mesailer"

    personel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("personel.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tarih: Mapped[date] = mapped_column(Date, nullable=False)
    saat: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    onayli: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )


class Zimmet(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Personele zimmetli demirbaş (iade edilene dek ``zimmetli``)."""

    __tablename__ = "zimmetler"

    personel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("personel.id", ondelete="CASCADE"), index=True, nullable=False
    )
    demirbas: Mapped[str] = mapped_column(String(200), nullable=False)
    seri_no: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    zimmet_tarihi: Mapped[date] = mapped_column(Date, nullable=False)
    iade_tarihi: Mapped[date | None] = mapped_column(Date, nullable=True)
    durum: Mapped[str] = mapped_column(String(20), default="zimmetli", index=True, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)


class Sertifika(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Personel sertifika / eğitim kaydı (``gecerlilik_tarihi`` geçerlilik sonu)."""

    __tablename__ = "sertifikalar"

    personel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("personel.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    kurum: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    belge_no: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    alinma_tarihi: Mapped[date] = mapped_column(Date, nullable=False)
    gecerlilik_tarihi: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
