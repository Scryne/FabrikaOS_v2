"""SQLAlchemy temel sınıfları, metadata ve ortak karışımlar (mixin).

İki ayrı metadata/Base kullanılır — bu, şema-başına-tenant (schema-per-tenant)
modelinin temelidir:

- ``PublicBase`` → control-plane tabloları; metadata ``schema="public"`` sabittir,
  böylece ``search_path`` ne olursa olsun bu tablolar her zaman ``public`` şemasında çözülür.
- ``TenantBase`` → iş modülü tabloları; metadata'da şema YOK. Tablo adı şema önekiyle
  yazılmaz; aktif istek oturumundaki ``search_path`` (``tenant_<slug>, public``) çözer.
  (Bkz. tenant-rbac-conventions: sabit ``tenant_xyz.tablo`` öneki yasaktır.)

``naming_convention`` zorunludur: kısıt/indeks adları öngörülebilir olur
(``ix_``, ``fk_``, ``uq_``, ``ck_``, ``pk_``) — fan-out ve şema karşılaştırmada hayat kurtarır.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Alembic ve fan-out için tutarlı kısıt/indeks adlandırması (alembic-fan-out skill'i).
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class PublicBase(DeclarativeBase):
    """Control-plane (public şema) modelleri için temel sınıf."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION, schema="public")


class TenantBase(DeclarativeBase):
    """Tenant şeması (tenant_<slug>) modelleri için temel sınıf — şema search_path ile çözülür."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class KimlikMixin:
    """BigInteger birincil anahtar (``id``)."""

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)


class ZamanDamgaliMixin:
    """``olusturma_tarihi`` / ``guncelleme_tarihi`` zaman damgaları (UTC, sunucu varsayılanı)."""

    olusturma_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    guncelleme_tarihi: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
