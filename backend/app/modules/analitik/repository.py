"""Analitik veri erişimi — modüller-arası salt-okunur toplulaştırma sorguları.

Sorgular aktif ``search_path``'e güvenir (tenant-rbac-conventions): şema adı yazılmaz,
çağıran katman oturumu tenant'a bağlamıştır. Ağır matematik SQL'de toplanır; OEE/fire
türetimi saf ``hesap`` katmanındadır.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.bakim.models import BakimPlani
from app.modules.enerji.models import EnerjiTuketim
from app.modules.isemri.durum import TERMINAL_DURUMLAR
from app.modules.isemri.models import IsEmri
from app.modules.isg.models import IsKazasi
from app.modules.kalite.models import KaliteKontrol, Uygunsuzluk
from app.modules.stok.models import Malzeme
from app.modules.uretim.models import Makine, UretimVerisi

_ACIK_ISEMRI_DURUMLARI = frozenset({"acik", "atandi", "devam_ediyor"})
assert not (_ACIK_ISEMRI_DURUMLARI & TERMINAL_DURUMLAR)


async def uretim_toplamlari(db: AsyncSession, *, esik: datetime) -> dict[str, Any]:
    """Dönem üretim bileşen toplamları (OEE girdileri)."""
    satir = (
        await db.execute(
            select(
                func.count().label("kayit_sayisi"),
                func.coalesce(func.sum(UretimVerisi.planlanan_sure_dk), 0.0).label("planlanan"),
                func.coalesce(func.sum(UretimVerisi.durus_sure_dk), 0.0).label("durus"),
                func.coalesce(func.sum(UretimVerisi.toplam_adet), 0).label("toplam_adet"),
                func.coalesce(func.sum(UretimVerisi.saglam_adet), 0).label("saglam_adet"),
                func.coalesce(
                    func.sum(UretimVerisi.ideal_cevrim_sn * UretimVerisi.toplam_adet), 0.0
                ).label("ideal_toplam_sn"),
            ).where(UretimVerisi.zaman >= esik)
        )
    ).one()
    return dict(satir._mapping)


async def makine_durum_kirilimi(db: AsyncSession) -> dict[str, int]:
    sonuc = await db.execute(select(Makine.durum, func.count()).group_by(Makine.durum))
    return {str(durum): int(adet) for durum, adet in sonuc.all()}


async def isemri_kpi(db: AsyncSession, *, esik: datetime) -> dict[str, Any]:
    acik = await db.scalar(
        select(func.count()).select_from(IsEmri).where(IsEmri.durum.in_(_ACIK_ISEMRI_DURUMLARI))
    )
    kapanan_filtre = (
        IsEmri.durum == "kapandi",
        IsEmri.kapanis_tarihi.is_not(None),
        IsEmri.kapanis_tarihi >= esik,
    )
    kapanan = await db.scalar(select(func.count()).select_from(IsEmri).where(*kapanan_filtre))
    ortalama_sn = await db.scalar(
        select(
            func.avg(func.extract("epoch", IsEmri.kapanis_tarihi - IsEmri.olusturma_tarihi))
        ).where(*kapanan_filtre)
    )
    return {
        "acik": int(acik or 0),
        "kapanan": int(kapanan or 0),
        "ortalama_kapanma_saat": None if ortalama_sn is None else float(ortalama_sn) / 3600.0,
    }


async def stok_kpi(db: AsyncSession) -> dict[str, int]:
    toplam = await db.scalar(
        select(func.count()).select_from(Malzeme).where(Malzeme.aktif.is_(True))
    )
    kritik = await db.scalar(
        select(func.count())
        .select_from(Malzeme)
        .where(
            Malzeme.aktif.is_(True),
            Malzeme.kritik_stok > 0,
            Malzeme.mevcut_miktar <= Malzeme.kritik_stok,
        )
    )
    return {"toplam_malzeme": int(toplam or 0), "kritik_sayisi": int(kritik or 0)}


async def kalite_kpi(db: AsyncSession, *, esik: datetime) -> dict[str, Any]:
    kontrol = await db.scalar(
        select(func.count()).select_from(KaliteKontrol).where(KaliteKontrol.zaman >= esik)
    )
    gecti = await db.scalar(
        select(func.count())
        .select_from(KaliteKontrol)
        .where(KaliteKontrol.zaman >= esik, KaliteKontrol.sonuc == "gecti")
    )
    acik_uygunsuzluk = await db.scalar(
        select(func.count())
        .select_from(Uygunsuzluk)
        .where(Uygunsuzluk.durum.not_in(("kapandi", "iptal")))
    )
    kontrol_sayisi = int(kontrol or 0)
    return {
        "kontrol_sayisi": kontrol_sayisi,
        "gecme_orani": None if kontrol_sayisi == 0 else int(gecti or 0) / kontrol_sayisi,
        "acik_uygunsuzluk": int(acik_uygunsuzluk or 0),
    }


async def enerji_kirilimi(db: AsyncSession, *, esik: datetime) -> list[dict[str, Any]]:
    """Dönem tüketimi tür+birim kırılımıyla (farklı birimler toplanmaz)."""
    sonuc = await db.execute(
        select(
            EnerjiTuketim.enerji_turu,
            EnerjiTuketim.birim,
            cast(func.sum(EnerjiTuketim.tuketim), Float).label("toplam"),
        )
        .where(EnerjiTuketim.zaman >= esik)
        .group_by(EnerjiTuketim.enerji_turu, EnerjiTuketim.birim)
        .order_by(EnerjiTuketim.enerji_turu, EnerjiTuketim.birim)
    )
    return [
        {"enerji_turu": str(tur), "birim": str(birim), "toplam": float(toplam)}
        for tur, birim, toplam in sonuc.all()
    ]


async def isg_kpi(db: AsyncSession, *, esik: datetime) -> dict[str, int]:
    olay = await db.scalar(
        select(func.count()).select_from(IsKazasi).where(IsKazasi.olay_tarihi >= esik)
    )
    kaza = await db.scalar(
        select(func.count())
        .select_from(IsKazasi)
        .where(IsKazasi.olay_tarihi >= esik, IsKazasi.tur == "kaza")
    )
    return {"olay_sayisi": int(olay or 0), "kaza_sayisi": int(kaza or 0)}


async def bakim_kpi(db: AsyncSession, *, simdi: datetime) -> dict[str, int]:
    aktif = await db.scalar(
        select(func.count()).select_from(BakimPlani).where(BakimPlani.aktif.is_(True))
    )
    geciken = await db.scalar(
        select(func.count())
        .select_from(BakimPlani)
        .where(
            BakimPlani.aktif.is_(True),
            BakimPlani.sonraki_bakim_tarihi.is_not(None),
            BakimPlani.sonraki_bakim_tarihi < simdi,
        )
    )
    return {"aktif_plan": int(aktif or 0), "geciken": int(geciken or 0)}


async def gunluk_uretim_serisi(db: AsyncSession, *, esik: datetime) -> list[dict[str, Any]]:
    """Günlük üretim bileşen toplamları (trend; artan tarih sırası)."""
    gun = func.date_trunc("day", UretimVerisi.zaman).label("gun")
    sonuc = await db.execute(
        select(
            gun,
            func.count().label("kayit_sayisi"),
            func.coalesce(func.sum(UretimVerisi.planlanan_sure_dk), 0.0).label("planlanan"),
            func.coalesce(func.sum(UretimVerisi.durus_sure_dk), 0.0).label("durus"),
            func.coalesce(func.sum(UretimVerisi.toplam_adet), 0).label("toplam_adet"),
            func.coalesce(func.sum(UretimVerisi.saglam_adet), 0).label("saglam_adet"),
            func.coalesce(
                func.sum(UretimVerisi.ideal_cevrim_sn * UretimVerisi.toplam_adet), 0.0
            ).label("ideal_toplam_sn"),
        )
        .where(UretimVerisi.zaman >= esik)
        .group_by(gun)
        .order_by(gun)
    )
    satirlar: list[dict[str, Any]] = []
    for satir in sonuc.all():
        veri = dict(satir._mapping)
        zaman = veri["gun"]
        veri["gun"] = zaman.date() if isinstance(zaman, datetime) else date.fromisoformat(zaman)
        satirlar.append(veri)
    return satirlar
