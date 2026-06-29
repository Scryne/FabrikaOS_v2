"""Domain olay outbox'ı (transactional outbox) — webhook altyapısına hazır iskelet.

Bir domain olayı (ör. ``is_emri.kapandi``) tetiklendiğinde, olayı üreten iş ile **aynı
veritabanı transaction'ında** ``giden_olaylar`` tablosuna bir satır yazılır. Bu, dual-write
sorununu önler: iş commit olduysa olay da kalıcıdır, olmadıysa ikisi de geri alınır.

Bu sprintte yalnızca **üretim/kayıt** tarafı vardır; teslimat (imzalama + retry + HTTP POST)
S18'de eklenecek bir relay tarafından ``durum='beklemede'`` satırları okunarak yapılır.
``dis_anahtar`` (UUID) dış tüketicilerin idempotency'si içindir. Tablo tenant şemasındadır;
böylece olaylar da kiracı-izole kalır.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import KimlikMixin, TenantBase, ZamanDamgaliMixin

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("app.olaylar")

# Outbox teslimat durumları.
OLAY_DURUMLARI = frozenset({"beklemede", "gonderildi", "basarisiz"})


class GidenOlay(KimlikMixin, ZamanDamgaliMixin, TenantBase):
    """Tenant şemasındaki giden domain olayı (webhook teslimatı için outbox satırı)."""

    __tablename__ = "giden_olaylar"

    dis_anahtar: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, index=True, nullable=False
    )
    olay_turu: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    govde: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    durum: Mapped[str] = mapped_column(String(20), default="beklemede", index=True, nullable=False)
    deneme_sayisi: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    gonderim_tarihi: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


async def olay_yayinla(
    session: AsyncSession, *, olay_turu: str, govde: dict[str, Any]
) -> GidenOlay:
    """Aktif tenant oturumuna bir outbox olayı ekler (flush eder, commit etmez).

    ``govde`` JSON-serileştirilebilir olmalıdır (datetime'lar ISO-8601 string olarak verilir).
    Çağıran iş ile aynı transaction'da çalışır → atomik.
    """
    olay = GidenOlay(olay_turu=olay_turu, govde=govde)
    session.add(olay)
    await session.flush()
    logger.info("domain olayı yayınlandı: %s (dis_anahtar=%s)", olay_turu, olay.dis_anahtar)
    return olay
