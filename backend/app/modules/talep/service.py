"""Talep iş kuralları — oto kod + durum geçişi (saf durum makinesine dayanır).

``sla_tara`` (S-VB) kenar-tetiklidir: hedef tarihi geçmiş ve hâlâ **çözülmemiş**
(``acik``/``inceleniyor``) talepler için ``sla.asildi`` olayını kaynak başına yalnız
bir kez yazar (dedup ``core.sla``). ``cozuldu`` SLA açısından karşılanmış sayılır.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import CakismaHatasi, DogrulamaHatasi
from app.core.sla import SlaAdayi, sla_asildi_yayinla
from app.modules.talep import durum as tdurum
from app.modules.talep.models import Talep

# SLA takibi süren durumlar (çözülmüş/terminal talepler olay üretmez).
SLA_ACIK_DURUMLAR = frozenset({"acik", "inceleniyor"})


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


async def sla_tara(db: AsyncSession, *, tenant_slug: str, simdi: datetime | None = None) -> int:
    """Hedef tarihi geçmiş çözülmemiş talepler için ``sla.asildi`` yazar (bir-kez)."""
    simdi = simdi or datetime.now(UTC)
    adaylar = (
        (
            await db.execute(
                select(Talep).where(
                    Talep.durum.in_(SLA_ACIK_DURUMLAR),
                    Talep.hedef_tarih.isnot(None),
                    Talep.hedef_tarih < simdi,
                )
            )
        )
        .scalars()
        .all()
    )
    return await sla_asildi_yayinla(
        db,
        tenant_slug=tenant_slug,
        kaynak_tur="talep",
        adaylar=[
            SlaAdayi(
                kaynak_id=t.id,
                kod=t.kod,
                hedef_tarih=t.hedef_tarih,  # type: ignore[arg-type]
                sorumlu_kullanici_id=t.atanan_kullanici_id,
            )
            for t in adaylar
        ],
    )
