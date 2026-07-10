"""Entegrasyon repository — webhook aboneliği + teslimat sorguları (şema-duyarsız).

Sorgular ``search_path``'e güvenir (tenant-rbac-conventions); şema adı asla elle yazılmaz.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.entegrasyon.models import WebhookAboneligi, WebhookTeslimati


async def abonelik_ekle(db: AsyncSession, abonelik: WebhookAboneligi) -> WebhookAboneligi:
    db.add(abonelik)
    await db.flush()
    return abonelik


async def abonelik_getir(db: AsyncSession, abonelik_id: int) -> WebhookAboneligi | None:
    sonuc = await db.execute(select(WebhookAboneligi).where(WebhookAboneligi.id == abonelik_id))
    return sonuc.scalar_one_or_none()


async def abonelik_listele(
    db: AsyncSession, *, sayfa: int, adet: int
) -> tuple[list[WebhookAboneligi], int]:
    toplam = (await db.execute(select(func.count()).select_from(WebhookAboneligi))).scalar_one()
    sonuc = await db.execute(
        select(WebhookAboneligi)
        .order_by(WebhookAboneligi.id.desc())
        .offset((sayfa - 1) * adet)
        .limit(adet)
    )
    return list(sonuc.scalars()), int(toplam)


async def abonelik_sil(db: AsyncSession, abonelik: WebhookAboneligi) -> None:
    await db.delete(abonelik)
    await db.flush()


async def teslimat_getir(db: AsyncSession, teslimat_id: int) -> WebhookTeslimati | None:
    sonuc = await db.execute(select(WebhookTeslimati).where(WebhookTeslimati.id == teslimat_id))
    return sonuc.scalar_one_or_none()


async def teslimat_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    abonelik_id: int | None = None,
    durum: str | None = None,
) -> tuple[list[WebhookTeslimati], int]:
    sorgu = select(WebhookTeslimati)
    if abonelik_id is not None:
        sorgu = sorgu.where(WebhookTeslimati.abonelik_id == abonelik_id)
    if durum is not None:
        sorgu = sorgu.where(WebhookTeslimati.durum == durum)
    toplam = (await db.execute(select(func.count()).select_from(sorgu.subquery()))).scalar_one()
    sonuc = await db.execute(
        sorgu.order_by(WebhookTeslimati.id.desc()).offset((sayfa - 1) * adet).limit(adet)
    )
    return list(sonuc.scalars()), int(toplam)
