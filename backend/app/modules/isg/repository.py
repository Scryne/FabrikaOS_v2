"""İSG veri erişimi (repository). Sorgular şema adı yazmaz; ``search_path`` çözer."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.isg.models import IsKazasi, RiskDegerlendirme

_KAZA_SIRALAMA = {
    "id": IsKazasi.id,
    "kod": IsKazasi.kod,
    "tur": IsKazasi.tur,
    "agirlik": IsKazasi.agirlik,
    "olay_tarihi": IsKazasi.olay_tarihi,
    "olusturma_tarihi": IsKazasi.olusturma_tarihi,
}

_RISK_SIRALAMA = {
    "id": RiskDegerlendirme.id,
    "kod": RiskDegerlendirme.kod,
    "risk_skoru": RiskDegerlendirme.risk_skoru,
    "risk_seviyesi": RiskDegerlendirme.risk_seviyesi,
    "durum": RiskDegerlendirme.durum,
    "olusturma_tarihi": RiskDegerlendirme.olusturma_tarihi,
}


async def kaza_ekle(db: AsyncSession, kaza: IsKazasi) -> IsKazasi:
    db.add(kaza)
    await db.flush()
    return kaza


async def kaza_getir(db: AsyncSession, kaza_id: int) -> IsKazasi | None:
    return await db.get(IsKazasi, kaza_id)


async def kaza_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    tur: str | None = None,
    agirlik: str | None = None,
    personel_id: int | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[IsKazasi], int]:
    filtreler: list[Any] = []
    if tur is not None:
        filtreler.append(IsKazasi.tur == tur)
    if agirlik is not None:
        filtreler.append(IsKazasi.agirlik == agirlik)
    if personel_id is not None:
        filtreler.append(IsKazasi.personel_id == personel_id)
    if arama:
        filtreler.append(IsKazasi.kod.ilike(f"%{arama}%"))

    kosul = select(IsKazasi)
    sayim = select(func.count()).select_from(IsKazasi)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_KAZA_SIRALAMA,
        varsayilan=IsKazasi.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


async def risk_ekle(db: AsyncSession, risk: RiskDegerlendirme) -> RiskDegerlendirme:
    db.add(risk)
    await db.flush()
    return risk


async def risk_getir(db: AsyncSession, risk_id: int) -> RiskDegerlendirme | None:
    return await db.get(RiskDegerlendirme, risk_id)


async def risk_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    durum: str | None = None,
    risk_seviyesi: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[RiskDegerlendirme], int]:
    filtreler: list[Any] = []
    if durum is not None:
        filtreler.append(RiskDegerlendirme.durum == durum)
    if risk_seviyesi is not None:
        filtreler.append(RiskDegerlendirme.risk_seviyesi == risk_seviyesi)
    if arama:
        filtreler.append(RiskDegerlendirme.kod.ilike(f"%{arama}%"))

    kosul = select(RiskDegerlendirme)
    sayim = select(func.count()).select_from(RiskDegerlendirme)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_RISK_SIRALAMA,
        varsayilan=RiskDegerlendirme.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)
