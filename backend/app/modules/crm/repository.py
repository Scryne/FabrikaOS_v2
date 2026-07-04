"""CRM veri erişimi (repository). Sorgular şema adı yazmaz; ``search_path`` çözer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.crm.models import Firma, Ortak

_FIRMA_SIRALAMA = {
    "id": Firma.id,
    "ad": Firma.ad,
    "tip": Firma.tip,
    "sektor": Firma.sektor,
    "il": Firma.il,
    "olusturma_tarihi": Firma.olusturma_tarihi,
}


# --- Firma ---
async def firma_ekle(db: AsyncSession, firma: Firma) -> Firma:
    db.add(firma)
    await db.flush()
    return firma


async def firma_getir(db: AsyncSession, firma_id: int) -> Firma | None:
    return await db.get(Firma, firma_id)


async def firma_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    tip: str | None = None,
    aktif: bool | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Firma], int]:
    filtreler: list[Any] = []
    if tip is not None:
        filtreler.append(Firma.tip == tip)
    if aktif is not None:
        filtreler.append(Firma.aktif == aktif)
    if arama:
        kalip = f"%{arama}%"
        filtreler.append(
            or_(Firma.ad.ilike(kalip), Firma.vergi_no.ilike(kalip), Firma.il.ilike(kalip))
        )

    kosul = select(Firma)
    sayim = select(func.count()).select_from(Firma)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_FIRMA_SIRALAMA,
        varsayilan=Firma.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


# --- Ortak ---
async def ortak_ekle(db: AsyncSession, ortak: Ortak) -> Ortak:
    db.add(ortak)
    await db.flush()
    return ortak


async def ortak_getir(db: AsyncSession, ortak_id: int) -> Ortak | None:
    return await db.get(Ortak, ortak_id)


async def ortak_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    firma_id: int | None = None,
    aktif: bool | None = None,
) -> tuple[Sequence[Ortak], int]:
    kosul = select(Ortak)
    sayim = select(func.count()).select_from(Ortak)
    if firma_id is not None:
        kosul = kosul.where(Ortak.firma_id == firma_id)
        sayim = sayim.where(Ortak.firma_id == firma_id)
    if aktif is not None:
        kosul = kosul.where(Ortak.aktif == aktif)
        sayim = sayim.where(Ortak.aktif == aktif)
    toplam = await db.scalar(sayim) or 0
    kosul = kosul.order_by(Ortak.birincil.desc(), Ortak.id.desc())
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)
