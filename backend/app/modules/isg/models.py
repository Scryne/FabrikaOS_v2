"""İSG modülü modelleri (tenant şeması) — iş kazası + risk değerlendirme.

- ``IsKazasi`` — iş kazası / ramak-kala / meslek hastalığı olay kaydı. ``personel_id`` (İK)
  yaralanan personeli, ``makine_id`` olayın makinesini opsiyonel bağlar.
- ``RiskDegerlendirme`` — risk matrisi değerlendirmesi; ``risk_skoru``/``risk_seviyesi``
  sunucuda ``risk_matrisi`` ile hesaplanır (istemciye güvenilmez).

FK'ler (``personel.id``/``makineler.id``/``kullanici.id``) şema öneki almaz; ``search_path`` çözer.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, func
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
