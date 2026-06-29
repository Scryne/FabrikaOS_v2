"""Tenant-kapsamlı kimlik ve RBAC modelleri.

İlişkisel model (tenant-rbac-conventions):
``kullanici`` n–n ``rol`` (``kullanici_rol``) · ``rol`` n–n ``izin`` (``rol_izin``).
İzin kodu biçimi: ``modul:islem`` (ör. ``uretim:yaz``, ``stok:oku``, ``satinalma:onay``).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

# --- n–n bağlantı tabloları ---
kullanici_rol = Table(
    "kullanici_rol",
    TenantBase.metadata,
    Column(
        "kullanici_id",
        BigInteger,
        ForeignKey("kullanici.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("rol_id", BigInteger, ForeignKey("rol.id", ondelete="CASCADE"), primary_key=True),
)

rol_izin = Table(
    "rol_izin",
    TenantBase.metadata,
    Column("rol_id", BigInteger, ForeignKey("rol.id", ondelete="CASCADE"), primary_key=True),
    Column("izin_id", BigInteger, ForeignKey("izin.id", ondelete="CASCADE"), primary_key=True),
)


class Izin(KimlikMixin, TenantBase):
    """Tekil yetki: ``kod`` = ``modul:islem`` (ör. ``uretim:yaz``)."""

    __tablename__ = "izin"

    kod: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(200), default="", nullable=False)

    roller: Mapped[list[Rol]] = relationship(secondary=rol_izin, back_populates="izinler")


class Rol(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Tenant'a özel rol; izinleri toplar, kullanıcılara atanır."""

    __tablename__ = "rol"

    ad: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    aciklama: Mapped[str] = mapped_column(String(200), default="", nullable=False)

    izinler: Mapped[list[Izin]] = relationship(
        secondary=rol_izin, back_populates="roller", lazy="selectin"
    )
    kullanicilar: Mapped[list[Kullanici]] = relationship(
        secondary=kullanici_rol, back_populates="roller"
    )


class Kullanici(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Tenant kullanıcısı; parola argon2id ile özetlenir."""

    __tablename__ = "kullanici"

    eposta: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    parola_ozet: Mapped[str] = mapped_column(String(255), nullable=False)
    ad_soyad: Mapped[str] = mapped_column(String(200), default="", nullable=False)
    aktif: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    son_giris_tarihi: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    roller: Mapped[list[Rol]] = relationship(
        secondary=kullanici_rol, back_populates="kullanicilar", lazy="selectin"
    )

    @property
    def izin_kodlari(self) -> set[str]:
        """Kullanıcının tüm rollerinden gelen izin kodları kümesi.

        ``roller`` ve ``roller.izinler`` önceden yüklenmiş olmalıdır (eager load).
        """
        return {izin.kod for rol in self.roller for izin in rol.izinler}

    def izin_var(self, kod: str) -> bool:
        return kod in self.izin_kodlari
