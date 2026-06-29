"""Bakım modülü veri erişimi (repository).

Sorgular şema adı yazmaz; aktif ``search_path`` (tenant şeması) çözer.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.bakim.models import BakimPlani

# Sıralanabilir kolon beyaz-listesi (istemci adı -> kolon).
_SIRALAMA = {
    "id": BakimPlani.id,
    "ad": BakimPlani.ad,
    "tip": BakimPlani.tip,
    "sonraki_bakim_tarihi": BakimPlani.sonraki_bakim_tarihi,
}


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
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[BakimPlani], int]:
    filtreler: list[Any] = []
    if makine_id is not None:
        filtreler.append(BakimPlani.makine_id == makine_id)
    if aktif is not None:
        filtreler.append(BakimPlani.aktif == aktif)
    if arama:
        filtreler.append(BakimPlani.ad.ilike(f"%{arama}%"))

    kosul = select(BakimPlani)
    sayim = select(func.count()).select_from(BakimPlani)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_SIRALAMA,
        varsayilan=BakimPlani.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)
