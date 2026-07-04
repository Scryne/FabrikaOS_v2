"""Duyuru veri erişimi (repository). Sorgular şema adı yazmaz; ``search_path`` çözer."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.duyuru.models import Duyuru


async def ekle(db: AsyncSession, duyuru: Duyuru) -> Duyuru:
    db.add(duyuru)
    await db.flush()
    return duyuru


async def getir(db: AsyncSession, duyuru_id: int) -> Duyuru | None:
    return await db.get(Duyuru, duyuru_id)


async def listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    onem: str | None = None,
    yayinda: bool | None = None,
) -> tuple[Sequence[Duyuru], int]:
    kosul = select(Duyuru)
    sayim = select(func.count()).select_from(Duyuru)
    if onem is not None:
        kosul = kosul.where(Duyuru.onem == onem)
        sayim = sayim.where(Duyuru.onem == onem)
    if yayinda is not None:
        kosul = kosul.where(Duyuru.yayinda == yayinda)
        sayim = sayim.where(Duyuru.yayinda == yayinda)
    toplam = await db.scalar(sayim) or 0
    kosul = kosul.order_by(Duyuru.yayin_tarihi.desc(), Duyuru.id.desc())
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)
