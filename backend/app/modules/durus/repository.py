"""Duruş repository'si — kayıt sorguları + pencere içi duruş dakikası toplamları.

``pencere_durus_dakikalari`` OEE entegrasyonunun tek kaynağıdır: verilen zaman
penceresiyle **kesişen** kayıtların kesişim süresi makine başına toplanır (kayıt
pencereden taşarsa yalnız pencere içindeki kısmı sayılır — çift sayım yok).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.durus.models import DurusKaydi, DurusNedeni


async def kayit_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    makine_id: int | None = None,
    neden_id: int | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
) -> tuple[list[DurusKaydi], int]:
    kosullar = []
    if makine_id is not None:
        kosullar.append(DurusKaydi.makine_id == makine_id)
    if neden_id is not None:
        kosullar.append(DurusKaydi.neden_id == neden_id)
    if baslangic is not None:
        kosullar.append(DurusKaydi.bitis >= baslangic)
    if bitis is not None:
        kosullar.append(DurusKaydi.baslangic <= bitis)
    toplam = (
        await db.execute(select(func.count()).select_from(DurusKaydi).where(*kosullar))
    ).scalar_one()
    kayitlar = (
        (
            await db.execute(
                select(DurusKaydi)
                .where(*kosullar)
                .order_by(DurusKaydi.baslangic.desc())
                .offset((sayfa - 1) * adet)
                .limit(adet)
            )
        )
        .scalars()
        .all()
    )
    return list(kayitlar), int(toplam)


def _kesisim_dk(baslangic: datetime | None, bitis: datetime | None) -> Any:
    """Pencereyle kesişim süresi (dakika) SQL ifadesi."""
    bas = (
        DurusKaydi.baslangic
        if baslangic is None
        else func.greatest(DurusKaydi.baslangic, baslangic)
    )
    bit = DurusKaydi.bitis if bitis is None else func.least(DurusKaydi.bitis, bitis)
    return func.extract("epoch", bit - bas) / 60.0


async def pencere_durus_dakikalari(
    db: AsyncSession,
    *,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    makine_id: int | None = None,
) -> dict[int, float]:
    """Pencereyle kesişen kayıtlı duruşların makine başına dakika toplamı."""
    kosullar = []
    if baslangic is not None:
        kosullar.append(DurusKaydi.bitis > baslangic)
    if bitis is not None:
        kosullar.append(DurusKaydi.baslangic < bitis)
    if makine_id is not None:
        kosullar.append(DurusKaydi.makine_id == makine_id)
    sorgu = (
        select(DurusKaydi.makine_id, func.sum(_kesisim_dk(baslangic, bitis)))
        .where(*kosullar)
        .group_by(DurusKaydi.makine_id)
    )
    satirlar = (await db.execute(sorgu)).all()
    return {int(mid): float(dk or 0.0) for mid, dk in satirlar}


async def pareto_girdileri(
    db: AsyncSession,
    *,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
) -> list[tuple[str, str, float]]:
    """Neden bazında (ad, sınıf, pencere içi toplam dakika) — saf pareto'nun girdisi."""
    kosullar = []
    if baslangic is not None:
        kosullar.append(DurusKaydi.bitis > baslangic)
    if bitis is not None:
        kosullar.append(DurusKaydi.baslangic < bitis)
    sorgu = (
        select(DurusNedeni.ad, DurusNedeni.sinif, func.sum(_kesisim_dk(baslangic, bitis)))
        .join(DurusKaydi, DurusKaydi.neden_id == DurusNedeni.id)
        .where(*kosullar)
        .group_by(DurusNedeni.ad, DurusNedeni.sinif)
    )
    satirlar = (await db.execute(sorgu)).all()
    return [(str(ad), str(sinif), float(dk or 0.0)) for ad, sinif, dk in satirlar]
