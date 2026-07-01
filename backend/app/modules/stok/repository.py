"""Stok & Satınalma veri erişimi (repository).

Sorgular şema adı yazmaz; aktif ``search_path`` (tenant şeması) çözer. Hareket ve
satınalma sorguları sonraki task'larda eklenir.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.stok.models import Malzeme

_MALZEME_SIRALAMA = {
    "id": Malzeme.id,
    "kod": Malzeme.kod,
    "ad": Malzeme.ad,
    "mevcut_miktar": Malzeme.mevcut_miktar,
    "kritik_stok": Malzeme.kritik_stok,
    "olusturma_tarihi": Malzeme.olusturma_tarihi,
}


async def malzeme_kod_var_mi(db: AsyncSession, kod: str) -> bool:
    return (await db.scalar(select(Malzeme.id).where(Malzeme.kod == kod))) is not None


async def malzeme_ekle(db: AsyncSession, malzeme: Malzeme) -> Malzeme:
    db.add(malzeme)
    await db.flush()
    return malzeme


async def malzeme_getir(db: AsyncSession, malzeme_id: int) -> Malzeme | None:
    return await db.get(Malzeme, malzeme_id)


async def malzeme_getir_kilitli(db: AsyncSession, malzeme_id: int) -> Malzeme | None:
    """Malzemeyi satır kilidiyle (``FOR UPDATE``) getirir — eşzamanlı stok hareketlerini
    seri hâle getirir, böylece bakiye çift güncellenmez."""
    sonuc = await db.execute(select(Malzeme).where(Malzeme.id == malzeme_id).with_for_update())
    return sonuc.scalar_one_or_none()


async def malzeme_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    arama: str | None = None,
    kategori: str | None = None,
    aktif: bool | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Malzeme], int]:
    filtreler: list[Any] = []
    if kategori is not None:
        filtreler.append(Malzeme.kategori == kategori)
    if aktif is not None:
        filtreler.append(Malzeme.aktif == aktif)
    if arama:
        kalip = f"%{arama}%"
        filtreler.append(or_(Malzeme.kod.ilike(kalip), Malzeme.ad.ilike(kalip)))

    kosul = select(Malzeme)
    sayim = select(func.count()).select_from(Malzeme)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_MALZEME_SIRALAMA,
        varsayilan=Malzeme.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


async def kritik_listele(db: AsyncSession) -> Sequence[Malzeme]:
    """Aktif + ``kritik_stok > 0`` + ``mevcut_miktar <= kritik_stok`` malzemeler."""
    kosul = (
        select(Malzeme)
        .where(Malzeme.aktif.is_(True))
        .where(Malzeme.kritik_stok > 0)
        .where(Malzeme.mevcut_miktar <= Malzeme.kritik_stok)
        .order_by(Malzeme.kod)
    )
    return (await db.execute(kosul)).scalars().all()
