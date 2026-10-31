"""İSG modülü modelleri (tenant şeması) — iş kazası + risk değerlendirme.

- ``IsKazasi`` — iş kazası / ramak-kala / meslek hastalığı olay kaydı. ``personel_id`` (İK)
  yaralanan personeli, ``makine_id`` olayın makinesini opsiyonel bağlar.
- ``RiskDegerlendirme`` — risk matrisi değerlendirmesi; ``risk_skoru``/``risk_seviyesi``
  sunucuda ``risk_matrisi`` ile hesaplanır (istemciye güvenilmez).

FK'ler (``personel.id``/``makineler.id``/``kullanici.id``) şema öneki almaz; ``search_path`` çözer.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin


class IsKazasi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """İş kazası / ramak-kala / meslek hastalığı olay kaydı."""

    __tablename__ = "is_kazalari"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    tur: Mapped[str] = mapped_column(String(20), default="kaza", index=True, nullable=False)
    olay_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    yer: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    aciklama: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    agirlik: Mapped[str] = mapped_column(String(20), default="hafif", index=True, nullable=False)
    kaybedilen_gun: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    yaralanma_turu: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    personel_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("personel.id", ondelete="SET NULL"), index=True, nullable=True
    )
    makine_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("makineler.id", ondelete="SET NULL"), index=True, nullable=True
    )
    raporlayan_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )


class RiskDegerlendirme(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Risk değerlendirme kaydı — risk matrisi (olasılık × şiddet)."""

    __tablename__ = "risk_degerlendirmeleri"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    baslik: Mapped[str] = mapped_column(String(200), nullable=False)
    bolum: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    tehlike: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    olasilik: Mapped[int] = mapped_column(Integer, nullable=False)
    siddet: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_skoru: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_seviyesi: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    onlem: Mapped[str] = mapped_column(String(2000), default="", nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default="acik", index=True, nullable=False)
    sorumlu_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    degerlendirme_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    gecerlilik_tarihi: Mapped[date | None] = mapped_column(Date, nullable=True)


# ---------------------------------------------------------------------------
# S26-B (ADR-0044): eğitim + katılım matrisi, KKD gereksinimi, acil durum tatbikatı.
# ---------------------------------------------------------------------------


class IsgEgitimi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Verilmiş bir İSG eğitimi oturumu; ``gecerlilik_ay`` tekrar sıklığı (0: süresiz)."""

    __tablename__ = "isg_egitimleri"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    konu: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    baslik: Mapped[str] = mapped_column(String(200), nullable=False)
    tarih: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    sure_saat: Mapped[Decimal] = mapped_column(Numeric(5, 1), default=Decimal("0"), nullable=False)
    egitmen: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    gecerlilik_ay: Mapped[int] = mapped_column(Integer, default=12, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(2000), default="", nullable=False)


class EgitimKatilimi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Eğitime katılan personel (eğitim × personel tekil)."""

    __tablename__ = "isg_egitim_katilimlari"
    __table_args__ = (UniqueConstraint("egitim_id", "personel_id", name="uq_egitim_katilim"),)

    egitim_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("isg_egitimleri.id", ondelete="CASCADE"), index=True, nullable=False
    )
    personel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("personel.id", ondelete="CASCADE"), index=True, nullable=False
    )


class EgitimGereksinimi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Departman için zorunlu eğitim konusu (``departman=''`` herkese)."""

    __tablename__ = "isg_egitim_gereksinimleri"
    __table_args__ = (UniqueConstraint("departman", "konu", name="uq_egitim_gereksinimi"),)

    departman: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    konu: Mapped[str] = mapped_column(String(100), nullable=False)


class KkdGereksinimi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Departman için zorunlu kişisel koruyucu donanım (``departman=''`` herkese)."""

    __tablename__ = "kkd_gereksinimleri"
    __table_args__ = (UniqueConstraint("departman", "kkd", name="uq_kkd_gereksinimi"),)

    departman: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    kkd: Mapped[str] = mapped_column(String(200), nullable=False)


class AcilDurumTatbikati(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Acil durum tatbikatı kaydı (yangın, deprem, tahliye, kimyasal sızıntı ...)."""

    __tablename__ = "acil_durum_tatbikatlari"

    kod: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    tur: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    tarih: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    yer: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    katilimci_sayisi: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tahliye_suresi_sn: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bulgular: Mapped[str] = mapped_column(String(4000), default="", nullable=False)
    sonraki_tarih: Mapped[date | None] = mapped_column(Date, nullable=True)
    yurutucu_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
