"""Stok & Satınalma veri erişimi (repository).

Sorgular şema adı yazmaz; aktif ``search_path`` (tenant şeması) çözer. Hareket ve
satınalma sorguları sonraki task'larda eklenir.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.sorgu import siralama_uygula
from app.modules.stok.models import Malzeme, SatinalmaTalebi, StokHareketi

_MALZEME_SIRALAMA = {
    "id": Malzeme.id,
    "kod": Malzeme.kod,
    "ad": Malzeme.ad,
    "mevcut_miktar": Malzeme.mevcut_miktar,
    "kritik_stok": Malzeme.kritik_stok,
    "olusturma_tarihi": Malzeme.olusturma_tarihi,
}


async def malzeme_kod_var_mi(db: AsyncSession, kod: str) -> bool:
    return (await db.scalar(select(Malzeme.id).where(Malzeme.kod == kod))) is not None


async def malzeme_ekle(db: AsyncSession, malzeme: Malzeme) -> Malzeme:
    db.add(malzeme)
    await db.flush()
    return malzeme


async def malzeme_getir(db: AsyncSession, malzeme_id: int) -> Malzeme | None:
    return await db.get(Malzeme, malzeme_id)


async def malzeme_getir_kilitli(db: AsyncSession, malzeme_id: int) -> Malzeme | None:
    """Malzemeyi satır kilidiyle (``FOR UPDATE``) getirir — eşzamanlı stok hareketlerini
    seri hâle getirir, böylece bakiye çift güncellenmez."""
    sonuc = await db.execute(select(Malzeme).where(Malzeme.id == malzeme_id).with_for_update())
    return sonuc.scalar_one_or_none()


async def malzeme_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    arama: str | None = None,
    kategori: str | None = None,
    aktif: bool | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Malzeme], int]:
    filtreler: list[Any] = []
    if kategori is not None:
        filtreler.append(Malzeme.kategori == kategori)
    if aktif is not None:
        filtreler.append(Malzeme.aktif == aktif)
    if arama:
        kalip = f"%{arama}%"
        filtreler.append(or_(Malzeme.kod.ilike(kalip), Malzeme.ad.ilike(kalip)))

    kosul = select(Malzeme)
    sayim = select(func.count()).select_from(Malzeme)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_MALZEME_SIRALAMA,
        varsayilan=Malzeme.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


async def kritik_listele(db: AsyncSession) -> Sequence[Malzeme]:
    """Aktif + ``kritik_stok > 0`` + ``mevcut_miktar <= kritik_stok`` malzemeler."""
    kosul = (
        select(Malzeme)
        .where(Malzeme.aktif.is_(True))
        .where(Malzeme.kritik_stok > 0)
        .where(Malzeme.mevcut_miktar <= Malzeme.kritik_stok)
        .order_by(Malzeme.kod)
    )
    return (await db.execute(kosul)).scalars().all()


_HAREKET_SIRALAMA = {
    "id": StokHareketi.id,
    "tur": StokHareketi.tur,
    "miktar": StokHareketi.miktar,
    "olusturma_tarihi": StokHareketi.olusturma_tarihi,
}


async def hareket_ekle(db: AsyncSession, hareket: StokHareketi) -> StokHareketi:
    db.add(hareket)
    await db.flush()
    return hareket


async def hareket_idempotent_getir(db: AsyncSession, anahtar: str) -> StokHareketi | None:
    sonuc = await db.execute(
        select(StokHareketi).where(StokHareketi.idempotency_anahtari == anahtar)
    )
    return sonuc.scalar_one_or_none()


async def hareket_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    malzeme_id: int | None = None,
    tur: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[StokHareketi], int]:
    filtreler: list[Any] = []
    if malzeme_id is not None:
        filtreler.append(StokHareketi.malzeme_id == malzeme_id)
    if tur is not None:
        filtreler.append(StokHareketi.tur == tur)
    if baslangic is not None:
        filtreler.append(StokHareketi.olusturma_tarihi >= baslangic)
    if bitis is not None:
        filtreler.append(StokHareketi.olusturma_tarihi <= bitis)

    kosul = select(StokHareketi)
    sayim = select(func.count()).select_from(StokHareketi)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_HAREKET_SIRALAMA,
        varsayilan=StokHareketi.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


_TALEP_SIRALAMA = {
    "id": SatinalmaTalebi.id,
    "kod": SatinalmaTalebi.kod,
    "baslik": SatinalmaTalebi.baslik,
    "durum": SatinalmaTalebi.durum,
    "olusturma_tarihi": SatinalmaTalebi.olusturma_tarihi,
}


async def talep_kod_var_mi(db: AsyncSession, kod: str) -> bool:
    return (
        await db.scalar(select(SatinalmaTalebi.id).where(SatinalmaTalebi.kod == kod))
    ) is not None


async def talep_ekle(db: AsyncSession, talep: SatinalmaTalebi) -> SatinalmaTalebi:
    db.add(talep)
    await db.flush()
    return talep


async def talep_getir(db: AsyncSession, talep_id: int) -> SatinalmaTalebi | None:
    return await db.get(SatinalmaTalebi, talep_id)


async def talep_getir_kilitli(db: AsyncSession, talep_id: int) -> SatinalmaTalebi | None:
    sonuc = await db.execute(
        select(SatinalmaTalebi).where(SatinalmaTalebi.id == talep_id).with_for_update()
    )
    return sonuc.scalar_one_or_none()


async def talep_getir_kalemli(db: AsyncSession, talep_id: int) -> SatinalmaTalebi | None:
    sonuc = await db.execute(
        select(SatinalmaTalebi)
        .where(SatinalmaTalebi.id == talep_id)
        .options(selectinload(SatinalmaTalebi.kalemler))
    )
    return sonuc.scalar_one_or_none()


async def talep_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    durum: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[SatinalmaTalebi], int]:
    filtreler: list[Any] = []
    if durum is not None:
        filtreler.append(SatinalmaTalebi.durum == durum)
    if arama:
        kalip = f"%{arama}%"
        filtreler.append(or_(SatinalmaTalebi.kod.ilike(kalip), SatinalmaTalebi.baslik.ilike(kalip)))

    kosul = select(SatinalmaTalebi)
    sayim = select(func.count()).select_from(SatinalmaTalebi)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_TALEP_SIRALAMA,
        varsayilan=SatinalmaTalebi.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)
