"""Talep veri erişimi (repository). Sorgular şema adı yazmaz; ``search_path`` çözer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.talep.models import Talep

_SIRALAMA = {
    "id": Talep.id,
    "kod": Talep.kod,
    "baslik": Talep.baslik,
    "oncelik": Talep.oncelik,
    "durum": Talep.durum,
    "olusturma_tarihi": Talep.olusturma_tarihi,
}


async def ekle(db: AsyncSession, talep: Talep) -> Talep:
    db.add(talep)
    await db.flush()
    return talep


async def getir(db: AsyncSession, talep_id: int) -> Talep | None:
    return await db.get(Talep, talep_id)


async def getir_kilitli(db: AsyncSession, talep_id: int) -> Talep | None:
    sonuc = await db.execute(select(Talep).where(Talep.id == talep_id).with_for_update())
    return sonuc.scalar_one_or_none()


async def listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    firma_id: int | None = None,
    durum: str | None = None,
    oncelik: str | None = None,
    tur: str | None = None,
    atanan_kullanici_id: int | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Talep], int]:
    filtreler: list[Any] = []
    if firma_id is not None:
        filtreler.append(Talep.firma_id == firma_id)
    if durum is not None:
        filtreler.append(Talep.durum == durum)
    if oncelik is not None:
        filtreler.append(Talep.oncelik == oncelik)
    if tur is not None:
        filtreler.append(Talep.tur == tur)
    if atanan_kullanici_id is not None:
        filtreler.append(Talep.atanan_kullanici_id == atanan_kullanici_id)
    if arama:
        kalip = f"%{arama}%"
        filtreler.append(or_(Talep.kod.ilike(kalip), Talep.baslik.ilike(kalip)))

    kosul = select(Talep)
    sayim = select(func.count()).select_from(Talep)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_SIRALAMA,
        varsayilan=Talep.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)
