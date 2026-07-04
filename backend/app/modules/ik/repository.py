"""İK veri erişimi (repository). Sorgular şema adı yazmaz; ``search_path`` çözer.

Kilit gereken izin talebi durum geçişleri ``izin_getir_kilitli`` (``FOR UPDATE``) kullanır
(çift onay / çift geçiş önlemek için, satınalma deseniyle aynı).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.sorgu import siralama_uygula
from app.modules.ik.models import FazlaMesai, IzinTalebi, Personel, Sertifika, Zimmet

_PERSONEL_SIRALAMA = {
    "id": Personel.id,
    "sicil_no": Personel.sicil_no,
    "ad": Personel.ad,
    "soyad": Personel.soyad,
    "departman": Personel.departman,
    "olusturma_tarihi": Personel.olusturma_tarihi,
}

_IZIN_SIRALAMA = {
    "id": IzinTalebi.id,
    "kod": IzinTalebi.kod,
    "baslangic_tarihi": IzinTalebi.baslangic_tarihi,
    "durum": IzinTalebi.durum,
    "olusturma_tarihi": IzinTalebi.olusturma_tarihi,
}


# --- Personel ---
async def personel_ekle(db: AsyncSession, personel: Personel) -> Personel:
    db.add(personel)
    await db.flush()
    return personel


async def personel_getir(db: AsyncSession, personel_id: int) -> Personel | None:
    return await db.get(Personel, personel_id)


async def personel_sicil_ile(db: AsyncSession, sicil_no: str) -> Personel | None:
    sonuc = await db.execute(select(Personel).where(Personel.sicil_no == sicil_no))
    return sonuc.scalar_one_or_none()


async def personel_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    departman: str | None = None,
    aktif: bool | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[Personel], int]:
    filtreler: list[Any] = []
    if departman is not None:
        filtreler.append(Personel.departman == departman)
    if aktif is not None:
        filtreler.append(Personel.aktif == aktif)
    if arama:
        kalip = f"%{arama}%"
        filtreler.append(
            or_(
                Personel.sicil_no.ilike(kalip),
                Personel.ad.ilike(kalip),
                Personel.soyad.ilike(kalip),
            )
        )

    kosul = select(Personel)
    sayim = select(func.count()).select_from(Personel)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_PERSONEL_SIRALAMA,
        varsayilan=Personel.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


# --- İzin talebi ---
async def izin_ekle(db: AsyncSession, izin: IzinTalebi) -> IzinTalebi:
    db.add(izin)
    await db.flush()
    return izin


async def izin_getir(db: AsyncSession, izin_id: int) -> IzinTalebi | None:
    return await db.get(IzinTalebi, izin_id)


async def izin_getir_kilitli(db: AsyncSession, izin_id: int) -> IzinTalebi | None:
    sonuc = await db.execute(select(IzinTalebi).where(IzinTalebi.id == izin_id).with_for_update())
    return sonuc.scalar_one_or_none()


async def izin_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    personel_id: int | None = None,
    durum: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> tuple[Sequence[IzinTalebi], int]:
    filtreler: list[Any] = []
    if personel_id is not None:
        filtreler.append(IzinTalebi.personel_id == personel_id)
    if durum is not None:
        filtreler.append(IzinTalebi.durum == durum)
    if arama:
        filtreler.append(IzinTalebi.kod.ilike(f"%{arama}%"))

    kosul = select(IzinTalebi)
    sayim = select(func.count()).select_from(IzinTalebi)
    for f in filtreler:
        kosul = kosul.where(f)
        sayim = sayim.where(f)
    toplam = await db.scalar(sayim) or 0
    kosul = siralama_uygula(
        kosul,
        siralama=siralama,
        yon=yon,
        izinli=_IZIN_SIRALAMA,
        varsayilan=IzinTalebi.id,
        varsayilan_yon="desc",
    )
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


# --- Fazla mesai ---
async def mesai_ekle(db: AsyncSession, mesai: FazlaMesai) -> FazlaMesai:
    db.add(mesai)
    await db.flush()
    return mesai


async def mesai_getir(db: AsyncSession, mesai_id: int) -> FazlaMesai | None:
    return await db.get(FazlaMesai, mesai_id)


async def mesai_listele(
    db: AsyncSession, *, sayfa: int, adet: int, personel_id: int | None = None
) -> tuple[Sequence[FazlaMesai], int]:
    kosul = select(FazlaMesai)
    sayim = select(func.count()).select_from(FazlaMesai)
    if personel_id is not None:
        kosul = kosul.where(FazlaMesai.personel_id == personel_id)
        sayim = sayim.where(FazlaMesai.personel_id == personel_id)
    toplam = await db.scalar(sayim) or 0
    kosul = kosul.order_by(FazlaMesai.id.desc())
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


# --- Zimmet ---
async def zimmet_ekle(db: AsyncSession, zimmet: Zimmet) -> Zimmet:
    db.add(zimmet)
    await db.flush()
    return zimmet


async def zimmet_getir(db: AsyncSession, zimmet_id: int) -> Zimmet | None:
    return await db.get(Zimmet, zimmet_id)


async def zimmet_listele(
    db: AsyncSession,
    *,
    sayfa: int,
    adet: int,
    personel_id: int | None = None,
    durum: str | None = None,
) -> tuple[Sequence[Zimmet], int]:
    kosul = select(Zimmet)
    sayim = select(func.count()).select_from(Zimmet)
    if personel_id is not None:
        kosul = kosul.where(Zimmet.personel_id == personel_id)
        sayim = sayim.where(Zimmet.personel_id == personel_id)
    if durum is not None:
        kosul = kosul.where(Zimmet.durum == durum)
        sayim = sayim.where(Zimmet.durum == durum)
    toplam = await db.scalar(sayim) or 0
    kosul = kosul.order_by(Zimmet.id.desc())
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)


# --- Sertifika ---
async def sertifika_ekle(db: AsyncSession, sertifika: Sertifika) -> Sertifika:
    db.add(sertifika)
    await db.flush()
    return sertifika


async def sertifika_listele(
    db: AsyncSession, *, sayfa: int, adet: int, personel_id: int | None = None
) -> tuple[Sequence[Sertifika], int]:
    kosul = select(Sertifika)
    sayim = select(func.count()).select_from(Sertifika)
    if personel_id is not None:
        kosul = kosul.where(Sertifika.personel_id == personel_id)
        sayim = sayim.where(Sertifika.personel_id == personel_id)
    toplam = await db.scalar(sayim) or 0
    kosul = kosul.order_by(Sertifika.id.desc())
    sonuc = await db.execute(kosul.offset((sayfa - 1) * adet).limit(adet))
    return sonuc.scalars().all(), int(toplam)
