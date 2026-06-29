"""İş emri modülü veri erişimi (repository).

Sorgular şema adı yazmaz; aktif istek oturumundaki ``search_path`` (tenant şeması) çözer
(tenant-rbac-conventions).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.kimlik.models import Kullanici
from app.modules.isemri.models import IsEmri, IsEmriYorum


async def kod_var_mi(db: AsyncSession, kod: str) -> bool:
    return (await db.scalar(select(IsEmri.id).where(IsEmri.kod == kod))) is not None


async def kullanici_var_mi(db: AsyncSession, kullanici_id: int) -> bool:
    return (await db.scalar(select(Kullanici.id).where(Kullanici.id == kullanici_id))) is not None


async def ekle(db: AsyncSession, is_emri: IsEmri) -> IsEmri:
    db.add(is_emri)
    await db.flush()
    return is_emri


async def getir(db: AsyncSession, is_emri_id: int) -> IsEmri | None:
    return await db.get(IsEmri, is_emri_id)


async def getir_kilitli(db: AsyncSession, is_emri_id: int) -> IsEmri | None:
    """İş emrini satır kilidiyle (``FOR UPDATE``) getirir — eşzamanlı durum geçişlerini
    seri hâle getirir, böylece çift kapanış/çift olay oluşmaz."""
    sonuc = await db.execute(select(IsEmri).where(IsEmri.id == is_emri_id).with_for_update())
    return sonuc.scalar_one_or_none()


async def getir_yorumlu(db: AsyncSession, is_emri_id: int) -> IsEmri | None:
    sonuc = await db.execute(
        select(IsEmri).where(IsEmri.id == is_emri_id).options(selectinload(IsEmri.yorumlar))
    )
    return sonuc.scalar_one_or_none()


async def listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    durum: str | None = None,
    makine_id: int | None = None,
    atanan_kullanici_id: int | None = None,
) -> tuple[Sequence[IsEmri], int]:
    filtreler: list[Any] = []
    if durum is not None:
        filtreler.append(IsEmri.durum == durum)
    if makine_id is not None:
        filtreler.append(IsEmri.makine_id == makine_id)
    if atanan_kullanici_id is not None:
        filtreler.append(IsEmri.atanan_kullanici_id == atanan_kullanici_id)

    kosul = select(IsEmri)
    sayim = select(func.count()).select_from(IsEmri)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    sonuc = await db.execute(
        kosul.order_by(IsEmri.id.desc()).offset((sayfa - 1) * adet).limit(adet)
    )
    return sonuc.scalars().all(), int(toplam)


async def yorum_ekle(db: AsyncSession, yorum: IsEmriYorum) -> IsEmriYorum:
    db.add(yorum)
    await db.flush()
    return yorum
