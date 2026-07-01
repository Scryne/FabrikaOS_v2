"""Kalite veri erişimi (repository). Sorgular şema adı yazmaz; ``search_path`` çözer.

Uygunsuzluk/aksiyon sorguları sonraki task'ta eklenir.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.kalite.models import KaliteKontrol

_KONTROL_SIRALAMA = {
    "id": KaliteKontrol.id,
    "kod": KaliteKontrol.kod,
    "sonuc": KaliteKontrol.sonuc,
    "zaman": KaliteKontrol.zaman,
    "olusturma_tarihi": KaliteKontrol.olusturma_tarihi,
}


async def kontrol_ekle(db: AsyncSession, kontrol: KaliteKontrol) -> KaliteKontrol:
    db.add(kontrol)
    await db.flush()
    return kontrol


async def kontrol_getir(db: AsyncSession, kontrol_id: int) -> KaliteKontrol | None:
    return await db.get(KaliteKontrol, kontrol_id)


async def kontrol_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    makine_id: int | None = None,
    sonuc: str | None = None,
    arama: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[KaliteKontrol], int]:
    filtreler: list[Any] = []
    if makine_id is not None:
        filtreler.append(KaliteKontrol.makine_id == makine_id)
    if sonuc is not None:
        filtreler.append(KaliteKontrol.sonuc == sonuc)
    if arama:
        filtreler.append(KaliteKontrol.kod.ilike(f"%{arama}%"))
    if baslangic is not None:
        filtreler.append(KaliteKontrol.zaman >= baslangic)
    if bitis is not None:
        filtreler.append(KaliteKontrol.zaman <= bitis)

    kosul = select(KaliteKontrol)
    sayim = select(func.count()).select_from(KaliteKontrol)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_KONTROL_SIRALAMA,
        varsayilan=KaliteKontrol.id,
        varsayilan_yon="desc",
    )
    sonuc_ = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc_.scalars().all(), int(toplam)
