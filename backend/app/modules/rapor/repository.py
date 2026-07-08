"""Rapor veri erişimi — kayıt CRUD + tür-bazlı rapor satırı sorguları.

Sorgular aktif ``search_path``'e güvenir (tenant-rbac-conventions). Satır sorguları
raporun tablo gövdesini üretir; başlık/özet biçimlendirmesi servis katmanındadır.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.enerji.models import EnerjiTuketim
from app.modules.isemri.models import IsEmri
from app.modules.kalite.models import KaliteKontrol
from app.modules.rapor.models import Rapor
from app.modules.stok.models import Malzeme
from app.modules.uretim.models import Makine, UretimVerisi


# --- Rapor kayıtları ---
async def rapor_getir(db: AsyncSession, rapor_id: int) -> Rapor | None:
    sonuc = await db.execute(select(Rapor).where(Rapor.id == rapor_id))
    return sonuc.scalar_one_or_none()


async def rapor_listele(
    db: AsyncSession,
    *,
    sayfa: int = 1,
    adet: int = 20,
    tur: str | None = None,
    durum: str | None = None,
) -> tuple[list[Rapor], int]:
    sorgu = select(Rapor).order_by(Rapor.id.desc())
    sayac = select(func.count(Rapor.id))
    if tur is not None:
        sorgu = sorgu.where(Rapor.tur == tur)
        sayac = sayac.where(Rapor.tur == tur)
    if durum is not None:
        sorgu = sorgu.where(Rapor.durum == durum)
        sayac = sayac.where(Rapor.durum == durum)
    toplam = int((await db.execute(sayac)).scalar() or 0)
    sonuc = await db.execute(sorgu.offset((sayfa - 1) * adet).limit(adet))
    return list(sonuc.scalars().all()), toplam


# --- Tür-bazlı rapor satırı kaynakları (aktif tenant şemasından) ---
async def uretim_satirlari(db: AsyncSession, *, esik: datetime) -> list[dict[str, Any]]:
    """Gün × makine üretim toplamları (OEE türetimi serviste)."""
    gun = func.date_trunc("day", UretimVerisi.zaman).label("gun")
    sonuc = await db.execute(
        select(
            gun,
            Makine.kod.label("makine_kod"),
            func.count().label("kayit_sayisi"),
            func.coalesce(func.sum(UretimVerisi.planlanan_sure_dk), 0.0).label("planlanan"),
            func.coalesce(func.sum(UretimVerisi.durus_sure_dk), 0.0).label("durus"),
            func.coalesce(func.sum(UretimVerisi.toplam_adet), 0).label("toplam_adet"),
            func.coalesce(func.sum(UretimVerisi.saglam_adet), 0).label("saglam_adet"),
            func.coalesce(
                func.sum(UretimVerisi.ideal_cevrim_sn * UretimVerisi.toplam_adet), 0.0
            ).label("ideal_toplam_sn"),
        )
        .join(Makine, Makine.id == UretimVerisi.makine_id)
        .where(UretimVerisi.zaman >= esik)
        .group_by(gun, Makine.kod)
        .order_by(gun, Makine.kod)
    )
    return [dict(satir._mapping) for satir in sonuc.all()]


async def stok_satirlari(db: AsyncSession) -> list[dict[str, Any]]:
    sonuc = await db.execute(
        select(
            Malzeme.kod,
            Malzeme.ad,
            Malzeme.kategori,
            Malzeme.birim,
            cast(Malzeme.mevcut_miktar, Float).label("mevcut"),
            cast(Malzeme.min_stok, Float).label("min_stok"),
            cast(Malzeme.kritik_stok, Float).label("kritik_stok"),
        )
        .where(Malzeme.aktif.is_(True))
        .order_by(Malzeme.kod)
    )
    return [dict(satir._mapping) for satir in sonuc.all()]


async def kalite_satirlari(db: AsyncSession, *, esik: datetime) -> list[dict[str, Any]]:
    sonuc = await db.execute(
        select(
            KaliteKontrol.kod,
            KaliteKontrol.zaman,
            KaliteKontrol.kontrol_turu,
            KaliteKontrol.sonuc,
            KaliteKontrol.numune_adedi,
            KaliteKontrol.uygunsuz_adet,
        )
        .where(KaliteKontrol.zaman >= esik)
        .order_by(KaliteKontrol.zaman)
    )
    return [dict(satir._mapping) for satir in sonuc.all()]


async def enerji_satirlari(db: AsyncSession, *, esik: datetime) -> list[dict[str, Any]]:
    gun = func.date_trunc("day", EnerjiTuketim.zaman).label("gun")
    sonuc = await db.execute(
        select(
            gun,
            EnerjiTuketim.enerji_turu,
            EnerjiTuketim.birim,
            cast(func.sum(EnerjiTuketim.tuketim), Float).label("toplam"),
        )
        .where(EnerjiTuketim.zaman >= esik)
        .group_by(gun, EnerjiTuketim.enerji_turu, EnerjiTuketim.birim)
        .order_by(gun, EnerjiTuketim.enerji_turu)
    )
    return [dict(satir._mapping) for satir in sonuc.all()]


async def isemri_satirlari(db: AsyncSession, *, esik: datetime) -> list[dict[str, Any]]:
    sonuc = await db.execute(
        select(
            IsEmri.kod,
            IsEmri.baslik,
            Makine.kod.label("makine_kod"),
            IsEmri.durum,
            IsEmri.oncelik,
            IsEmri.olusturma_tarihi,
            IsEmri.kapanis_tarihi,
        )
        .join(Makine, Makine.id == IsEmri.makine_id)
        .where(IsEmri.olusturma_tarihi >= esik)
        .order_by(IsEmri.olusturma_tarihi)
    )
    return [dict(satir._mapping) for satir in sonuc.all()]
