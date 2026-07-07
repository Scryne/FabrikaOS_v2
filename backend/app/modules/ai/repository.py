"""AI veri erişimi — model kaydı/tahmin CRUD + feature pipeline'a DataFrame kaynakları.

DataFrame çekiciler aktif ``search_path``'e güvenir (tenant-rbac-conventions): sorgular
şema adı yazmaz, çağıran katman oturumu tenant'a bağlamıştır. Kolon adları
``ozellikler.py`` girdi sözleşmesiyle birebir aynıdır.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai.models import ModelKaydi, Tahmin
from app.modules.stok.models import Malzeme, StokHareketi
from app.modules.uretim.models import ArizaKaydi, UretimVerisi


# --- ModelKaydi ---
async def kayit_getir(db: AsyncSession, kayit_id: int) -> ModelKaydi | None:
    sonuc = await db.execute(select(ModelKaydi).where(ModelKaydi.id == kayit_id))
    return sonuc.scalar_one_or_none()


async def kayit_listele(db: AsyncSession, *, tur: str | None = None) -> list[ModelKaydi]:
    sorgu = select(ModelKaydi).order_by(ModelKaydi.id.desc())
    if tur is not None:
        sorgu = sorgu.where(ModelKaydi.tur == tur)
    sonuc = await db.execute(sorgu)
    return list(sonuc.scalars().all())


async def sonraki_surum(db: AsyncSession, tur: str) -> int:
    sonuc = await db.execute(select(func.max(ModelKaydi.surum)).where(ModelKaydi.tur == tur))
    return int(sonuc.scalar() or 0) + 1


async def aktif_kayit(db: AsyncSession, tur: str) -> ModelKaydi | None:
    sonuc = await db.execute(
        select(ModelKaydi).where(
            ModelKaydi.tur == tur,
            ModelKaydi.durum == "hazir",
            ModelKaydi.aktif.is_(True),
        )
    )
    return sonuc.scalar_one_or_none()


async def aktifleri_pasifle(db: AsyncSession, tur: str, *, haric_id: int) -> None:
    """Aynı türdeki diğer aktif kayıtları pasifler (tur başına tek aktif kuralı)."""
    await db.execute(
        update(ModelKaydi)
        .where(ModelKaydi.tur == tur, ModelKaydi.aktif.is_(True), ModelKaydi.id != haric_id)
        .values(aktif=False)
    )


# --- Tahmin geçmişi ---
async def tahmin_ekle(db: AsyncSession, tahmin: Tahmin) -> Tahmin:
    db.add(tahmin)
    await db.flush()
    return tahmin


async def tahmin_listele(
    db: AsyncSession, *, tur: str | None = None, sayfa: int = 1, adet: int = 20
) -> tuple[list[Tahmin], int]:
    sorgu = select(Tahmin).order_by(Tahmin.id.desc())
    sayac = select(func.count(Tahmin.id))
    if tur is not None:
        sorgu = sorgu.where(Tahmin.tur == tur)
        sayac = sayac.where(Tahmin.tur == tur)
    toplam = int((await db.execute(sayac)).scalar() or 0)
    sonuc = await db.execute(sorgu.offset((sayfa - 1) * adet).limit(adet))
    return list(sonuc.scalars().all()), toplam


# --- Feature pipeline veri kaynakları (aktif tenant şemasından) ---
async def uretim_cercevesi(db: AsyncSession, *, gun: int = 90) -> pd.DataFrame:
    esik = datetime.now(UTC) - timedelta(days=gun)
    sonuc = await db.execute(
        select(
            UretimVerisi.zaman,
            UretimVerisi.makine_id,
            UretimVerisi.planlanan_sure_dk,
            UretimVerisi.durus_sure_dk,
            UretimVerisi.toplam_adet,
            UretimVerisi.saglam_adet,
            UretimVerisi.ideal_cevrim_sn,
        ).where(UretimVerisi.zaman >= esik)
    )
    return pd.DataFrame(sonuc.mappings().all())


async def ariza_cercevesi(db: AsyncSession, *, gun: int = 365) -> pd.DataFrame:
    esik = datetime.now(UTC) - timedelta(days=gun)
    sonuc = await db.execute(
        select(ArizaKaydi.makine_id, ArizaKaydi.baslangic).where(ArizaKaydi.baslangic >= esik)
    )
    return pd.DataFrame(sonuc.mappings().all())


async def stok_hareket_cercevesi(db: AsyncSession, *, gun: int = 90) -> pd.DataFrame:
    esik = datetime.now(UTC) - timedelta(days=gun)
    sonuc = await db.execute(
        select(
            StokHareketi.malzeme_id,
            StokHareketi.tur,
            StokHareketi.miktar,
            StokHareketi.olusturma_tarihi.label("zaman"),
        ).where(StokHareketi.olusturma_tarihi >= esik)
    )
    return pd.DataFrame(sonuc.mappings().all())


async def malzeme_cercevesi(db: AsyncSession) -> pd.DataFrame:
    sonuc = await db.execute(
        select(
            Malzeme.id.label("malzeme_id"),
            Malzeme.kod,
            Malzeme.ad,
            Malzeme.birim,
            Malzeme.mevcut_miktar,
            Malzeme.kritik_stok,
        ).where(Malzeme.aktif.is_(True))
    )
    return pd.DataFrame(sonuc.mappings().all())
