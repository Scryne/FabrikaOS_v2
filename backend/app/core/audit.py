"""Denetim izi (audit trail) — tenant şemasında kim-ne-ne zaman kaydı.

Yazma işlemleri (POST/PATCH/PUT/DELETE) bu tabloya kaydedilir. ``request_id`` istek
bağlamından alınır; ``tenant`` log korelasyonu zaten ``logging``/``context`` tarafından sağlanır.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.context import request_id_ctx
from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.kimlik.models import Kullanici


class DenetimIzi(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Tenant şemasındaki denetim kaydı."""

    __tablename__ = "denetim_izi"

    kullanici_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    kullanici_eposta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    eylem: Mapped[str] = mapped_column(String(50), nullable=False)
    kaynak: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    kaynak_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ip_adresi: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detay: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)


async def denetim_yaz(
    session: AsyncSession,
    *,
    eylem: str,
    kaynak: str,
    kaynak_id: str | None = None,
    kullanici: Kullanici | None = None,
    ip_adresi: str | None = None,
    detay: dict[str, Any] | None = None,
) -> DenetimIzi:
    """Aktif tenant oturumuna bir denetim kaydı ekler (flush eder, commit etmez)."""
    kayit = DenetimIzi(
        kullanici_id=kullanici.id if kullanici is not None else None,
        kullanici_eposta=kullanici.eposta if kullanici is not None else None,
        eylem=eylem,
        kaynak=kaynak,
        kaynak_id=kaynak_id,
        request_id=request_id_ctx.get(),
        ip_adresi=ip_adresi,
        detay=detay,
    )
    session.add(kayit)
    await session.flush()
    return kayit
