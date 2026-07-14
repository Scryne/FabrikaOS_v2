"""Bildirim repository'si — tüm sorgular oturum kullanıcısına zorlanır.

Kişisel yüzey: fonksiyonlar ``kullanici_id`` parametresini şart koşar; başka
kullanıcının bildirimi yapısal olarak görünmez/erişilmez (404 üst katmanda).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bildirim.models import Bildirim, BildirimTercihi


async def listele(
    db: AsyncSession,
    *,
    kullanici_id: int,
    sayfa: int,
    adet: int,
    okundu: bool | None = None,
    olay_turu: str | None = None,
) -> tuple[list[Bildirim], int]:
    """Oturum kullanıcısının bildirimleri (yeniden eskiye) + toplam sayı."""
    kosullar = [Bildirim.kullanici_id == kullanici_id]
    if okundu is not None:
        kosullar.append(Bildirim.okundu == okundu)
    if olay_turu:
        kosullar.append(Bildirim.olay_turu == olay_turu)
    toplam = (
        await db.execute(select(func.count()).select_from(Bildirim).where(*kosullar))
    ).scalar_one()
    kayitlar = (
        (
            await db.execute(
                select(Bildirim)
                .where(*kosullar)
                .order_by(Bildirim.id.desc())
                .offset((sayfa - 1) * adet)
                .limit(adet)
            )
        )
        .scalars()
        .all()
    )
    return list(kayitlar), int(toplam)


async def ozet(db: AsyncSession, *, kullanici_id: int) -> tuple[int, int, list[Bildirim]]:
    """(okunmamış, toplam, son 5 bildirim) — zil rozeti beslemesi."""
    okunmamis = (
        await db.execute(
            select(func.count())
            .select_from(Bildirim)
            .where(Bildirim.kullanici_id == kullanici_id, Bildirim.okundu.is_(False))
        )
    ).scalar_one()
    toplam = (
        await db.execute(
            select(func.count()).select_from(Bildirim).where(Bildirim.kullanici_id == kullanici_id)
        )
    ).scalar_one()
    son = (
        (
            await db.execute(
                select(Bildirim)
                .where(Bildirim.kullanici_id == kullanici_id)
                .order_by(Bildirim.id.desc())
                .limit(5)
            )
        )
        .scalars()
        .all()
    )
    return int(okunmamis), int(toplam), list(son)


async def getir(db: AsyncSession, bildirim_id: int, *, kullanici_id: int) -> Bildirim | None:
    """Kullanıcının kendi bildirimi (başkasınınki görünmez → None)."""
    return (
        await db.execute(
            select(Bildirim).where(
                Bildirim.id == bildirim_id, Bildirim.kullanici_id == kullanici_id
            )
        )
    ).scalar_one_or_none()


async def tumunu_okundu_yap(db: AsyncSession, *, kullanici_id: int) -> int:
    """Oturum kullanıcısının tüm okunmamışlarını okundu işaretler; sayıyı döner."""
    sonuc = await db.execute(
        update(Bildirim)
        .where(Bildirim.kullanici_id == kullanici_id, Bildirim.okundu.is_(False))
        .values(okundu=True, okundu_tarihi=datetime.now(UTC))
        .returning(Bildirim.id)
    )
    await db.flush()
    return len(sonuc.scalars().all())


async def tercihleri_getir(db: AsyncSession, *, kullanici_id: int) -> list[BildirimTercihi]:
    return list(
        (
            await db.execute(
                select(BildirimTercihi).where(BildirimTercihi.kullanici_id == kullanici_id)
            )
        )
        .scalars()
        .all()
    )


async def tercih_upsert(
    db: AsyncSession, *, kullanici_id: int, olay_turu: str, uygulama_ici: bool, eposta: bool
) -> BildirimTercihi:
    """Kullanıcının olay türü tercihini oluşturur/günceller."""
    mevcut = (
        await db.execute(
            select(BildirimTercihi).where(
                BildirimTercihi.kullanici_id == kullanici_id,
                BildirimTercihi.olay_turu == olay_turu,
            )
        )
    ).scalar_one_or_none()
    if mevcut is None:
        mevcut = BildirimTercihi(kullanici_id=kullanici_id, olay_turu=olay_turu)
        db.add(mevcut)
    mevcut.uygulama_ici = uygulama_ici
    mevcut.eposta = eposta
    await db.flush()
    return mevcut
