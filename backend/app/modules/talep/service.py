"""Talep iş kuralları — oto kod + durum geçişi (saf durum makinesine dayanır)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi
from app.modules.talep import durum as tdurum
from app.modules.talep.models import Talep


def talep_gecici_kod() -> str:
    return f"GECICI-{uuid.uuid4().hex}"


def talep_kalici_kod(talep_id: int) -> str:
    """İnsan-okur talep numarası: ``TL-{yıl}-{id:06d}``."""
    return f"TL-{datetime.now(UTC).year}-{talep_id:06d}"


async def talep_durum_gecisi(db: AsyncSession, talep: Talep, *, hedef: str) -> Talep:
    """Talebi ``hedef`` duruma geçirir (tanımsız → 422; makineye aykırı → 409)."""
    if hedef not in tdurum.DURUMLAR:
        raise DogrulamaHatasi(
            "Geçersiz durum",
            detaylar=[{"alan": "durum", "mesaj": f"Geçerli: {', '.join(sorted(tdurum.DURUMLAR))}"}],
        )
    if not tdurum.gecis_gecerli_mi(talep.durum, hedef):
        raise CakismaHatasi(f"Geçersiz durum geçişi: {talep.durum} → {hedef}")
    talep.durum = hedef
    await db.flush()
    return talep
