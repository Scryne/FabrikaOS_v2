"""CRM modülü modelleri (tenant şeması) — firma + ortak (ilgili kişi).

- ``Firma`` — müşteri/tedarikçi cari kaydı. ``sorumlu_kullanici_id`` firmayı bir hesap
  yöneticisine opsiyonel bağlar.
- ``Ortak`` — firmadaki ilgili kişi (kontak). ``birincil`` firmanın ana kontağını işaretler.

FK'ler şema önekiyle yazılmaz (``firmalar.id``, ``kullanici.id``); ``search_path`` çözer.
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin


class Firma(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Cari firma (müşteri/tedarikçi) kaydı."""

    __tablename__ = "firmalar"

    ad: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    tip: Mapped[str] = mapped_column(String(20), default="musteri", index=True, nullable=False)
    vergi_no: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    vergi_dairesi: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    telefon: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    eposta: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    adres: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    il: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    sektor: Mapped[str] = mapped_column(String(100), default="", index=True, nullable=False)
    web_sitesi: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    sorumlu_kullanici_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("kullanici.id", ondelete="SET NULL"), index=True, nullable=True
    )
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(2000), default="", nullable=False)


class Ortak(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Firmadaki ilgili kişi (kontak); ``birincil`` ana kontağı işaretler."""

    __tablename__ = "ortaklar"

    firma_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("firmalar.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ad_soyad: Mapped[str] = mapped_column(String(200), nullable=False)
    unvan: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    telefon: Mapped[str] = mapped_column(String(30), default="", nullable=False)
    eposta: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    birincil: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(1000), default="", nullable=False)
