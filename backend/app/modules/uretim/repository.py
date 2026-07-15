"""Üretim modülü veri erişimi (repository).

Sorgular şema adı yazmaz; aktif istek oturumundaki ``search_path`` (tenant şeması) çözer.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.uretim.models import Makine, UretimVerisi

# Sıralanabilir kolon beyaz-listeleri (istemci adı -> kolon).
_MAKINE_SIRALAMA = {
    "id": Makine.id,
    "kod": Makine.kod,
    "ad": Makine.ad,
    "durum": Makine.durum,
}
_URETIM_SIRALAMA = {
    "zaman": UretimVerisi.zaman,
    "toplam_adet": UretimVerisi.toplam_adet,
    "saglam_adet": UretimVerisi.saglam_adet,
    "durus_sure_dk": UretimVerisi.durus_sure_dk,
}


@dataclass(frozen=True, slots=True)
class OeeToplam:
    """OEE hesabı için toplulaştırılmış girdiler."""

    planlanan_sure_dk: float
    durus_sure_dk: float
    toplam_adet: int
    saglam_adet: int
    ideal_sure_dk: float  # sum(ideal_cevrim_sn * toplam_adet) / 60
    kayit_sayisi: int


async def makine_kod_var_mi(db: AsyncSession, kod: str) -> bool:
    return (await db.scalar(select(Makine.id).where(Makine.kod == kod))) is not None


async def makine_ekle(db: AsyncSession, makine: Makine) -> Makine:
    db.add(makine)
    await db.flush()
    return makine


async def makine_getir(db: AsyncSession, makine_id: int) -> Makine | None:
    return await db.get(Makine, makine_id)


async def makine_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    durum: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Makine], int]:
    kosul = select(Makine)
    sayim = select(func.count()).select_from(Makine)
    if durum is not None:
        kosul = kosul.where(Makine.durum == durum)
        sayim = sayim.where(Makine.durum == durum)
    if arama:
        kalip = f"%{arama}%"
        filtre = or_(Makine.kod.ilike(kalip), Makine.ad.ilike(kalip))
        kosul = kosul.where(filtre)
        sayim = sayim.where(filtre)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul, siralama=siralama, yon=yon, izinli=_MAKINE_SIRALAMA, varsayilan=Makine.id
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


async def uretim_ekle(db: AsyncSession, kayit: UretimVerisi) -> UretimVerisi:
    db.add(kayit)
    await db.flush()
    return kayit


async def uretim_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    makine_id: int | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[UretimVerisi], int]:
    kosul = select(UretimVerisi)
    sayim = select(func.count()).select_from(UretimVerisi)
    for filtre in _zaman_filtreleri(makine_id, baslangic, bitis):
        kosul = kosul.where(filtre)
        sayim = sayim.where(filtre)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_URETIM_SIRALAMA,
        varsayilan=UretimVerisi.zaman,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


def _zaman_filtreleri(
    makine_id: int | None, baslangic: datetime | None, bitis: datetime | None
) -> list[Any]:
    filtreler: list[Any] = []
    if makine_id is not None:
        filtreler.append(UretimVerisi.makine_id == makine_id)
    if baslangic is not None:
        filtreler.append(UretimVerisi.zaman >= baslangic)
    if bitis is not None:
        filtreler.append(UretimVerisi.zaman <= bitis)
    return filtreler


def _topla(row: Sequence[Any]) -> OeeToplam:
    plan, durus, toplam, saglam, ideal_carpim, sayi = row
    return OeeToplam(
        planlanan_sure_dk=float(plan or 0),
        durus_sure_dk=float(durus or 0),
        toplam_adet=int(toplam or 0),
        saglam_adet=int(saglam or 0),
        ideal_sure_dk=float(ideal_carpim or 0) / 60.0,
        kayit_sayisi=int(sayi or 0),
    )


_OEE_KOLONLARI = (
    func.coalesce(func.sum(UretimVerisi.planlanan_sure_dk), 0.0),
    func.coalesce(func.sum(UretimVerisi.durus_sure_dk), 0.0),
    func.coalesce(func.sum(UretimVerisi.toplam_adet), 0),
    func.coalesce(func.sum(UretimVerisi.saglam_adet), 0),
    func.coalesce(func.sum(UretimVerisi.ideal_cevrim_sn * UretimVerisi.toplam_adet), 0.0),
    func.count(),
)


async def oee_toplam(
    db: AsyncSession,
    makine_id: int,
    *,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    vardiya: str | None = None,
) -> OeeToplam:
    sorgu = select(*_OEE_KOLONLARI).where(UretimVerisi.makine_id == makine_id)
    for filtre in _zaman_filtreleri(None, baslangic, bitis):
        sorgu = sorgu.where(filtre)
    if vardiya is not None:
        sorgu = sorgu.where(UretimVerisi.vardiya == vardiya)
    row = (await db.execute(sorgu)).one()
    return _topla(row)


async def oee_ozet(
    db: AsyncSession,
    *,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    vardiya: str | None = None,
) -> list[tuple[int, str, OeeToplam]]:
    sorgu = (
        select(Makine.id, Makine.kod, *_OEE_KOLONLARI)
        .join(UretimVerisi, UretimVerisi.makine_id == Makine.id)
        .group_by(Makine.id, Makine.kod)
        .order_by(Makine.id)
    )
    for filtre in _zaman_filtreleri(None, baslangic, bitis):
        sorgu = sorgu.where(filtre)
    if vardiya is not None:
        sorgu = sorgu.where(UretimVerisi.vardiya == vardiya)
    satirlar = (await db.execute(sorgu)).all()
    return [(r[0], r[1], _topla(r[2:])) for r in satirlar]
