"""Dijital ikiz veri erişimi.

Sorgular aktif ``search_path``'e güvenir (tenant-rbac-conventions): şema adı yazılmaz,
çağıran katman oturumu tenant'a bağlamıştır. OEE türetimi saf katmandadır
(``analitik.hesap.donem_oee``); burada yalnız SQL toplamları vardır.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ikiz.models import IkizDugum
from app.modules.uretim.models import ArizaKaydi, Makine, UretimVerisi


async def dugumleri_getir(db: AsyncSession) -> list[IkizDugum]:
    sonuc = await db.execute(select(IkizDugum).order_by(IkizDugum.id))
    return list(sonuc.scalars().all())


async def yerlesimi_degistir(db: AsyncSession, dugumler: list[dict[str, Any]]) -> list[IkizDugum]:
    """Yerleşimi bütün olarak değiştirir (replace-all, idempotent)."""
    await db.execute(delete(IkizDugum))
    kayitlar = [IkizDugum(**d) for d in dugumler]
    db.add_all(kayitlar)
    await db.flush()
    return kayitlar


async def makineleri_getir(db: AsyncSession) -> list[Makine]:
    sonuc = await db.execute(select(Makine).order_by(Makine.kod))
    return list(sonuc.scalars().all())


async def makine_id_kumesi(db: AsyncSession) -> set[int]:
    sonuc = await db.execute(select(Makine.id))
    return {int(mid) for (mid,) in sonuc.all()}


async def makine_pencere_toplamlari(
    db: AsyncSession, *, esik: datetime
) -> dict[int, dict[str, Any]]:
    """Pencere içi üretim bileşen toplamları, makine bazında (OEE girdileri)."""
    sonuc = await db.execute(
        select(
            UretimVerisi.makine_id,
            func.count().label("kayit_sayisi"),
            func.coalesce(func.sum(UretimVerisi.planlanan_sure_dk), 0.0).label("planlanan"),
            func.coalesce(func.sum(UretimVerisi.durus_sure_dk), 0.0).label("durus"),
            func.coalesce(func.sum(UretimVerisi.toplam_adet), 0).label("toplam_adet"),
            func.coalesce(func.sum(UretimVerisi.saglam_adet), 0).label("saglam_adet"),
            func.coalesce(
                func.sum(UretimVerisi.ideal_cevrim_sn * UretimVerisi.toplam_adet), 0.0
            ).label("ideal_toplam_sn"),
            func.max(UretimVerisi.zaman).label("son_veri_zamani"),
        )
        .where(UretimVerisi.zaman >= esik)
        .group_by(UretimVerisi.makine_id)
    )
    return {int(satir.makine_id): dict(satir._mapping) for satir in sonuc.all()}


async def acik_ariza_sayisi(db: AsyncSession) -> int:
    sayi = await db.scalar(
        select(func.count()).select_from(ArizaKaydi).where(ArizaKaydi.cozuldu.is_(False))
    )
    return int(sayi or 0)
