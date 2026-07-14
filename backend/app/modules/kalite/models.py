"""Kalite modülü modelleri (tenant şeması) — denetim + Tam CAPA.

- ``KaliteKontrol`` — denetim/muayene kaydı (makine + opsiyonel iş emri).
- ``Uygunsuzluk`` — CAPA vakası; durum ``durum.py`` makinesiyle yönetilir; ``kok_neden``
  kök-neden aşamasında dolar.
- ``CapaAksiyon`` — düzeltici/önleyici aksiyon (n–1 uygunsuzluk); kendi durumu vardır.

FK'ler şema önekiyle yazılmaz (``makineler.id``, ``kullanici.id``); ``search_path`` çözer.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin
from app.modules.kalite.durum import ILK_DURUM

_OLCU = Numeric(18, 3)


class KaliteKontrol(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Kalite denetim/muayene kaydı."""

    __tablename__ = "kalite_kontrolleri"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    makine_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="SET NULL"), index=True, nullable=True
    )
    is_emri_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("is_emirleri.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # Giriş kalite kontrolü malzeme bağlantısı (S-VB): tedarikçi skoru kalite bileşeni.
    malzeme_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("malzemeler.id", ondelete="SET NULL"), index=True, nullable=True
    )
    kontrol_turu: Mapped[str] = mapped_column(String(20), default="uretim", nullable=False)
    sonuc: Mapped[str] = mapped_column(String(20), nullable=False)
    olculen_deger: Mapped[Decimal | None] = mapped_column(_OLCU, nullable=True)
    alt_limit: Mapped[Decimal | None] = mapped_column(_OLCU, nullable=True)
    ust_limit: Mapped[Decimal | None] = mapped_column(_OLCU, nullable=True)
    numune_adedi: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    uygunsuz_adet: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    kontrol_eden_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    zaman: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Uygunsuzluk(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Uygunsuzluk / CAPA vakası — yaşam döngüsü ``durum.py``."""

    __tablename__ = "uygunsuzluklar"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    baslik: Mapped[str] = mapped_column(String(200), nullable=False)
    aciklama: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    kaynak_kontrol_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("kalite_kontrolleri.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    makine_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="SET NULL"), index=True, nullable=True
    )
    onem: Mapped[str] = mapped_column(String(20), default="orta", index=True, nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default=ILK_DURUM, index=True, nullable=False)
    kok_neden: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    acan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    sorumlu_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    dogrulama_notu: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    kapanis_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    aksiyonlar: Mapped[list[CapaAksiyon]] = relationship(
        back_populates="uygunsuzluk",
        cascade="all, delete-orphan",
        order_by="CapaAksiyon.id",
    )


class CapaAksiyon(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Düzeltici/önleyici aksiyon (n–1 uygunsuzluk)."""

    __tablename__ = "capa_aksiyonlari"

    uygunsuzluk_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("uygunsuzluklar.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    tur: Mapped[str] = mapped_column(String(20), nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), nullable=False)
    sorumlu_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    termin_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    durum: Mapped[str] = mapped_column(String(20), default="planlandi", nullable=False)
    tamamlanma_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    uygunsuzluk: Mapped[Uygunsuzluk] = relationship(back_populates="aksiyonlar")
