"""Platform denetim izi yazıcısı — ``public.platform_denetim_izi``.

Tenant ``core/audit.py``'nin control-plane aynası: platform yazma işlemleri
(provizyon, askıya alma, silme, entitlement, ihraç) buradan kaydedilir.
``request_id``/``ip_adresi`` istek bağlamından otomatik alınır.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import PlatformDenetimIzi, PlatformYonetici
from app.core.context import istemci_ip_ctx, request_id_ctx


async def platform_denetim_yaz(
    session: AsyncSession,
    *,
    eylem: str,
    kaynak: str,
    kaynak_id: str | None = None,
    yonetici: PlatformYonetici | None = None,
    detay: dict[str, Any] | None = None,
) -> PlatformDenetimIzi:
    """Platform denetim kaydı ekler (flush eder, commit etmez)."""
    kayit = PlatformDenetimIzi(
        yonetici_id=yonetici.id if yonetici is not None else None,
        yonetici_eposta=yonetici.eposta if yonetici is not None else None,
        eylem=eylem,
        kaynak=kaynak,
        kaynak_id=kaynak_id,
        request_id=request_id_ctx.get(),
        ip_adresi=istemci_ip_ctx.get(),
        detay=detay,
    )
    session.add(kayit)
    await session.flush()
    return kayit
