"""Kalite veri erişimi (repository). Sorgular şema adı yazmaz; ``search_path`` çözer.

Uygunsuzluk/aksiyon sorguları sonraki task'ta eklenir.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.sorgu import siralama_uygula
from app.modules.kalite.models import CapaAksiyon, KaliteKontrol, Uygunsuzluk

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


_UYGUNSUZLUK_SIRALAMA = {
    "id": Uygunsuzluk.id,
    "kod": Uygunsuzluk.kod,
    "baslik": Uygunsuzluk.baslik,
    "onem": Uygunsuzluk.onem,
    "durum": Uygunsuzluk.durum,
    "olusturma_tarihi": Uygunsuzluk.olusturma_tarihi,
}


async def uygunsuzluk_ekle(db: AsyncSession, u: Uygunsuzluk) -> Uygunsuzluk:
    db.add(u)
    await db.flush()
    return u


async def uygunsuzluk_getir(db: AsyncSession, uid: int) -> Uygunsuzluk | None:
    return await db.get(Uygunsuzluk, uid)


async def uygunsuzluk_getir_kilitli(db: AsyncSession, uid: int) -> Uygunsuzluk | None:
    sonuc = await db.execute(select(Uygunsuzluk).where(Uygunsuzluk.id == uid).with_for_update())
    return sonuc.scalar_one_or_none()


async def uygunsuzluk_getir_aksiyonlu(db: AsyncSession, uid: int) -> Uygunsuzluk | None:
    sonuc = await db.execute(
        select(Uygunsuzluk)
        .where(Uygunsuzluk.id == uid)
        .options(selectinload(Uygunsuzluk.aksiyonlar))
    )
    return sonuc.scalar_one_or_none()


async def aksiyon_getir(db: AsyncSession, aksiyon_id: int) -> CapaAksiyon | None:
    return await db.get(CapaAksiyon, aksiyon_id)


async def uygunsuzluk_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    durum: str | None = None,
    onem: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Uygunsuzluk], int]:
    filtreler: list[Any] = []
    if durum is not None:
        filtreler.append(Uygunsuzluk.durum == durum)
    if onem is not None:
        filtreler.append(Uygunsuzluk.onem == onem)
    if arama:
        kalip = f"%{arama}%"
        filtreler.append(or_(Uygunsuzluk.kod.ilike(kalip), Uygunsuzluk.baslik.ilike(kalip)))

    kosul = select(Uygunsuzluk)
    sayim = select(func.count()).select_from(Uygunsuzluk)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_UYGUNSUZLUK_SIRALAMA,
        varsayilan=Uygunsuzluk.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)
