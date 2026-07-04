"""Sözleşme veri erişimi (repository). Sorgular şema adı yazmaz; ``search_path`` çözer.

Durum geçişi ``sozlesme_getir_kilitli`` (``FOR UPDATE``) ile satır kilidi kullanır
(çift geçiş / yaklaşan olayı yarışını önler).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.sozlesme.models import Sozlesme

_SIRALAMA = {
    "id": Sozlesme.id,
    "kod": Sozlesme.kod,
    "baslik": Sozlesme.baslik,
    "bitis_tarihi": Sozlesme.bitis_tarihi,
    "tutar": Sozlesme.tutar,
    "durum": Sozlesme.durum,
    "olusturma_tarihi": Sozlesme.olusturma_tarihi,
}


async def ekle(db: AsyncSession, sozlesme: Sozlesme) -> Sozlesme:
    db.add(sozlesme)
    await db.flush()
    return sozlesme


async def getir(db: AsyncSession, sozlesme_id: int) -> Sozlesme | None:
    return await db.get(Sozlesme, sozlesme_id)


async def getir_kilitli(db: AsyncSession, sozlesme_id: int) -> Sozlesme | None:
    sonuc = await db.execute(select(Sozlesme).where(Sozlesme.id == sozlesme_id).with_for_update())
    return sonuc.scalar_one_or_none()


async def listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    firma_id: int | None = None,
    durum: str | None = None,
    tur: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Sozlesme], int]:
    filtreler: list[Any] = []
    if firma_id is not None:
        filtreler.append(Sozlesme.firma_id == firma_id)
    if durum is not None:
        filtreler.append(Sozlesme.durum == durum)
    if tur is not None:
        filtreler.append(Sozlesme.tur == tur)
    if arama:
        kalip = f"%{arama}%"
        filtreler.append(or_(Sozlesme.kod.ilike(kalip), Sozlesme.baslik.ilike(kalip)))

    kosul = select(Sozlesme)
    sayim = select(func.count()).select_from(Sozlesme)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_SIRALAMA,
        varsayilan=Sozlesme.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


async def yaklasan_listele(db: AsyncSession, *, bugun: date, sinir: date) -> Sequence[Sozlesme]:
    """Aktif + bitişi ``[bugun, sinir]`` aralığındaki sözleşmeler (yaklaşan görünüm)."""
    sonuc = await db.execute(
        select(Sozlesme)
        .where(Sozlesme.durum == "aktif")
        .where(Sozlesme.bitis_tarihi >= bugun)
        .where(Sozlesme.bitis_tarihi <= sinir)
        .order_by(Sozlesme.bitis_tarihi.asc())
    )
    return sonuc.scalars().all()


async def yaklasan_bildirilmemis(db: AsyncSession, *, bugun: date, sinir: date) -> list[Sozlesme]:
    """Yaklaşan + henüz ``sozlesme.yaklasiyor`` üretilmemiş sözleşmeler (kenar-tetik)."""
    sonuc = await db.execute(
        select(Sozlesme)
        .where(Sozlesme.durum == "aktif")
        .where(Sozlesme.bitis_tarihi >= bugun)
        .where(Sozlesme.bitis_tarihi <= sinir)
        .where(Sozlesme.yaklasim_bildirildi.is_(False))
        .with_for_update()
    )
    return list(sonuc.scalars().all())
