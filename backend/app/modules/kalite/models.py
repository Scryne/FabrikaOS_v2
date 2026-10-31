"""Kalite modülü modelleri (tenant şeması) — denetim + Tam CAPA.

- ``KaliteKontrol`` — denetim/muayene kaydı (makine + opsiyonel iş emri).
- ``Uygunsuzluk`` — CAPA vakası; durum ``durum.py`` makinesiyle yönetilir; ``kok_neden``
  kök-neden aşamasında dolar.
- ``CapaAksiyon`` — düzeltici/önleyici aksiyon (n–1 uygunsuzluk); kendi durumu vardır.

FK'ler şema önekiyle yazılmaz (``makineler.id``, ``kullanici.id``); ``search_path`` çözer.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
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
    # S26: kaynak tedarikçi ise (giriş muayenesi); skor formülü değişmedi (ADR-0025 §6).
    tedarikci_firma_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("firmalar.id", ondelete="SET NULL"), index=True, nullable=True
    )
    makine_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="SET NULL"), index=True, nullable=True
    )
    # S26-B kaza → CAPA köprüsü: kaza başına tek vaka (UNIQUE), ADR-0044.
    kaynak_kaza_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("is_kazalari.id", ondelete="SET NULL"),
        unique=True,
        index=True,
        nullable=True,
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


# ── S26 kalite olgunluğu (ADR-0025): ölçüm cihazı + kalibrasyon, kontrol planı + SPC ─────────

CIHAZ_DURUMLARI = frozenset({"aktif", "kullanim_disi", "hurda"})
KALIBRASYON_SONUCLARI = frozenset({"uygun", "ayarlandi", "uygunsuz"})


class OlcumCihazi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Ölçüm cihazı. Geçerlilik ``sonraki_kalibrasyon_tarihi``nden okunur; süresi geçmiş ya da
    kullanım dışı cihazla SPC ölçümü girilmez (ISO 9001 7.1.5)."""

    __tablename__ = "olcum_cihazlari"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    tur: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    seri_no: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    konum: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    kalibrasyon_periyodu_gun: Mapped[int] = mapped_column(Integer, default=365, nullable=False)
    son_kalibrasyon_tarihi: Mapped[date | None] = mapped_column(Date, nullable=True)
    sonraki_kalibrasyon_tarihi: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    durum: Mapped[str] = mapped_column(String(20), default="aktif", index=True, nullable=False)
    sorumlu_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )
    # Kenar tetikli hatırlatma: yeni kalibrasyon kaydı bayrağı sıfırlar (S12 sözleşme deseni).
    yaklasim_bildirildi: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class KalibrasyonKaydi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "kalibrasyon_kayitlari"

    cihaz_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("olcum_cihazlari.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tarih: Mapped[date] = mapped_column(Date, nullable=False)
    sonuc: Mapped[str] = mapped_column(String(20), nullable=False)
    sertifika_no: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    kurum: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    belge_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("belgeler.id", ondelete="SET NULL"), nullable=True
    )
    kaydeden_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )


class KontrolPlani(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "kontrol_planlari"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    urun_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("urunler.id", ondelete="SET NULL"), index=True, nullable=True
    )
    operasyon: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    olusturan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )

    karakteristikler: Mapped[list[KontrolKarakteristigi]] = relationship(
        back_populates="plan", cascade="all, delete-orphan", order_by="KontrolKarakteristigi.sira"
    )


class KontrolKarakteristigi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Planın ölçülen bir özelliği (ör. "Mil çapı"); SPC kartı karakteristik başınadır."""

    __tablename__ = "kontrol_karakteristikleri"

    plan_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("kontrol_planlari.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sira: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ad: Mapped[str] = mapped_column(String(200), nullable=False)
    birim: Mapped[str] = mapped_column(String(20), default="mm", nullable=False)
    nominal: Mapped[Decimal | None] = mapped_column(_OLCU, nullable=True)
    alt_tolerans: Mapped[Decimal | None] = mapped_column(_OLCU, nullable=True)
    ust_tolerans: Mapped[Decimal | None] = mapped_column(_OLCU, nullable=True)
    alt_grup_boyutu: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    olcum_yontemi: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    cihaz_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("olcum_cihazlari.id", ondelete="SET NULL"), nullable=True
    )
    # Faz-I'den sabitlenen limitler (None = her çizimde tüm alt gruplardan hesaplanır).
    sabit_limitler: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    plan: Mapped[KontrolPlani] = relationship(back_populates="karakteristikler")


class SpcAltGrup(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    __tablename__ = "spc_alt_gruplari"
    __table_args__ = (
        UniqueConstraint("karakteristik_id", "sira", name="uq_spc_alt_gruplari_sira"),
    )

    karakteristik_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("kontrol_karakteristikleri.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    sira: Mapped[int] = mapped_column(Integer, nullable=False)
    zaman: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    degerler: Mapped[list[float]] = mapped_column(JSONB, nullable=False)
    cihaz_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("olcum_cihazlari.id", ondelete="SET NULL"), nullable=True
    )
    olcen_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), nullable=True
    )
    # Girildiği anda bu noktanın tamamladığı kural ihlalleri (kart sonradan yeniden çizilse de
    # "o gün ne gördük" kaydı kalır).
    ihlaller: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(500), default="", nullable=False)
