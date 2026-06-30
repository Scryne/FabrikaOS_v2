"""Saha modülü veri erişimi. Sorgular şema yazmaz; ``search_path`` (tenant) çözer."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.saha.models import AlinanOlcum, Cihaz
from app.modules.uretim.models import Makine

_CIHAZ_SIRALAMA = {
    "id": Cihaz.id,
    "kod": Cihaz.kod,
    "ad": Cihaz.ad,
    "protokol": Cihaz.protokol,
    "son_gorulme": Cihaz.son_gorulme,
}


async def cihaz_kod_var_mi(session: AsyncSession, kod: str) -> bool:
    return (await session.scalar(select(Cihaz.id).where(Cihaz.kod == kod))) is not None


async def cihaz_ekle(session: AsyncSession, cihaz: Cihaz) -> Cihaz:
    session.add(cihaz)
    await session.flush()
    return cihaz


async def cihaz_getir(session: AsyncSession, cihaz_id: int) -> Cihaz | None:
    return await session.get(Cihaz, cihaz_id)


async def cihaz_kod_ile(session: AsyncSession, kod: str) -> Cihaz | None:
    sonuc = await session.execute(select(Cihaz).where(Cihaz.kod == kod))
    return sonuc.scalars().first()


async def cihaz_listele(
    session: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Cihaz], int]:
    kosul = select(Cihaz)
    sayim = select(func.count()).select_from(Cihaz)
    if arama:
        kalip = f"%{arama}%"
        filtre = or_(Cihaz.kod.ilike(kalip), Cihaz.ad.ilike(kalip))
        kosul = kosul.where(filtre)
        sayim = sayim.where(filtre)
    toplam = await session.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul, siralama=siralama, yon=yon, izinli=_CIHAZ_SIRALAMA, varsayilan=Cihaz.id
    )
    sonuc = await session.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


async def makine_id_kod_ile(session: AsyncSession, makine_kod: str) -> int | None:
    sonuc = await session.scalar(select(Makine.id).where(Makine.kod == makine_kod))
    return None if sonuc is None else int(sonuc)


async def olcum_isaretle(session: AsyncSession, olcum_id: UUID, makine_id: int) -> bool:
    """Idempotency defterine ekle. Yeni ise True; zaten varsa (çift) False.

    ``RETURNING`` + ``ON CONFLICT DO NOTHING``: çakışmada satır dönmez → False.
    """
    stmt = (
        pg_insert(AlinanOlcum)
        .values(olcum_id=olcum_id, makine_id=makine_id)
        .on_conflict_do_nothing(index_elements=["olcum_id"])
        .returning(AlinanOlcum.olcum_id)
    )
    return (await session.scalar(stmt)) is not None
