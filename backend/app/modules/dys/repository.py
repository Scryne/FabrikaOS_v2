"""DYS veri erişimi (repository). Sorgular şema adı yazmaz; ``search_path`` çözer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.dys.models import Belge, BelgeSurumu

_SIRALAMA = {
    "id": Belge.id,
    "kod": Belge.kod,
    "ad": Belge.ad,
    "kategori": Belge.kategori,
    "olusturma_tarihi": Belge.olusturma_tarihi,
}


# --- Belge ---
async def belge_ekle(db: AsyncSession, belge: Belge) -> Belge:
    db.add(belge)
    await db.flush()
    return belge


async def belge_getir(db: AsyncSession, belge_id: int) -> Belge | None:
    return await db.get(Belge, belge_id)


async def belge_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    kategori: str | None = None,
    aktif: bool | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Belge], int]:
    filtreler: list[Any] = []
    if kategori is not None:
        filtreler.append(Belge.kategori == kategori)
    if aktif is not None:
        filtreler.append(Belge.aktif == aktif)
    if arama:
        kalip = f"%{arama}%"
        filtreler.append(or_(Belge.kod.ilike(kalip), Belge.ad.ilike(kalip)))

    kosul = select(Belge)
    sayim = select(func.count()).select_from(Belge)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_SIRALAMA,
        varsayilan=Belge.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


# --- Belge sürümü ---
async def surum_listele(db: AsyncSession, belge_id: int) -> Sequence[BelgeSurumu]:
    sonuc = await db.execute(
        select(BelgeSurumu)
        .where(BelgeSurumu.belge_id == belge_id)
        .order_by(BelgeSurumu.surum_no.desc())
    )
    return sonuc.scalars().all()


async def surum_getir(db: AsyncSession, belge_id: int, surum_no: int) -> BelgeSurumu | None:
    sonuc = await db.execute(
        select(BelgeSurumu)
        .where(BelgeSurumu.belge_id == belge_id)
        .where(BelgeSurumu.surum_no == surum_no)
    )
    return sonuc.scalar_one_or_none()
