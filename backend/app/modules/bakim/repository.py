"""Bakım modülü veri erişimi (repository).

Sorgular şema adı yazmaz; aktif ``search_path`` (tenant şeması) çözer.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bakim.models import BakimPlani


async def ekle(db: AsyncSession, plan: BakimPlani) -> BakimPlani:
    db.add(plan)
    await db.flush()
    return plan


async def getir(db: AsyncSession, plan_id: int) -> BakimPlani | None:
    return await db.get(BakimPlani, plan_id)


async def listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    makine_id: int | None = None,
    aktif: bool | None = None,
) -> tuple[Sequence[BakimPlani], int]:
    filtreler: list[Any] = []
    if makine_id is not None:
        filtreler.append(BakimPlani.makine_id == makine_id)
    if aktif is not None:
        filtreler.append(BakimPlani.aktif == aktif)

    kosul = select(BakimPlani)
    sayim = select(func.count()).select_from(BakimPlani)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    sonuc = await db.execute(
        kosul.order_by(BakimPlani.id.desc()).offset((sayfa - 1) * adet).limit(adet)
    )
    return sonuc.scalars().all(), int(toplam)
