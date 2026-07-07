"""Analitik uçları (``/api/v1/analitik``) — modüller-arası KPI + günlük üretim trendi.

Salt-okunur toplulaştırma; migration/tablo yoktur. Tüm uçlar tenant-kapsamlı +
``analitik:oku`` korumalı. Enerji trendi S10'daki ``/enerji-tuketimleri/trend``
(continuous aggregate) ucundan servis edilir — burada çoğaltılmaz.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.responses import Zarf, basari
from app.kimlik.models import Kullanici
from app.modules.analitik import repository
from app.modules.analitik.hesap import donem_oee, fire_orani
from app.modules.analitik.schemas import (
    BakimKpiDTO,
    EnerjiKpiDTO,
    IsEmriKpiDTO,
    IsgKpiDTO,
    KaliteKpiDTO,
    KpiCevapDTO,
    MakineKpiDTO,
    StokKpiDTO,
    TrendNoktasiDTO,
    UretimKpiDTO,
)

router = APIRouter(prefix="/analitik", tags=["Analitik"])

_GunParam = Annotated[int, Query(ge=1, le=365, description="Geriye dönük pencere (gün)")]


def _uretim_kpi(toplamlar: dict[str, Any]) -> UretimKpiDTO:
    toplam_adet = int(toplamlar["toplam_adet"])
    saglam_adet = int(toplamlar["saglam_adet"])
    oee = donem_oee(
        planlanan_sure_dk=float(toplamlar["planlanan"]),
        durus_sure_dk=float(toplamlar["durus"]),
        toplam_adet=toplam_adet,
        saglam_adet=saglam_adet,
        ideal_toplam_sn=float(toplamlar["ideal_toplam_sn"]),
    )
    return UretimKpiDTO(
        kayit_sayisi=int(toplamlar["kayit_sayisi"]),
        toplam_adet=toplam_adet,
        saglam_adet=saglam_adet,
        fire_orani=fire_orani(toplam_adet, saglam_adet),
        kullanilabilirlik=oee.kullanilabilirlik,
        performans=oee.performans,
        kalite=oee.kalite,
        oee=oee.oee,
    )


@router.get("/kpi", response_model=Zarf[KpiCevapDTO], summary="Modüller-arası KPI özeti")
async def kpi_ozeti(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("analitik:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    gun: _GunParam = 30,
) -> dict[str, Any]:
    simdi = datetime.now(UTC)
    esik = simdi - timedelta(days=gun)

    uretim = await repository.uretim_toplamlari(db, esik=esik)
    durumlar = await repository.makine_durum_kirilimi(db)
    isemri = await repository.isemri_kpi(db, esik=esik)
    stok = await repository.stok_kpi(db)
    kalite = await repository.kalite_kpi(db, esik=esik)
    enerji = await repository.enerji_kirilimi(db, esik=esik)
    isg = await repository.isg_kpi(db, esik=esik)
    bakim = await repository.bakim_kpi(db, simdi=simdi)

    cevap = KpiCevapDTO(
        gun=gun,
        baslangic=esik,
        bitis=simdi,
        uretim=_uretim_kpi(uretim),
        makine=MakineKpiDTO(toplam=sum(durumlar.values()), durumlar=durumlar),
        isemri=IsEmriKpiDTO(**isemri),
        stok=StokKpiDTO(**stok),
        kalite=KaliteKpiDTO(**kalite),
        enerji=EnerjiKpiDTO(kirilim=enerji),
        isg=IsgKpiDTO(**isg),
        bakim=BakimKpiDTO(**bakim),
    )
    return basari(cevap.model_dump(), mesaj="KPI özeti")


@router.get(
    "/trend",
    response_model=Zarf[list[TrendNoktasiDTO]],
    summary="Günlük üretim/OEE trendi",
)
async def uretim_trendi(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("analitik:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    gun: _GunParam = 30,
) -> dict[str, Any]:
    esik = datetime.now(UTC) - timedelta(days=gun)
    seri = await repository.gunluk_uretim_serisi(db, esik=esik)
    noktalar: list[dict[str, Any]] = []
    for satir in seri:
        toplam_adet = int(satir["toplam_adet"])
        saglam_adet = int(satir["saglam_adet"])
        oee = donem_oee(
            planlanan_sure_dk=float(satir["planlanan"]),
            durus_sure_dk=float(satir["durus"]),
            toplam_adet=toplam_adet,
            saglam_adet=saglam_adet,
            ideal_toplam_sn=float(satir["ideal_toplam_sn"]),
        )
        noktalar.append(
            TrendNoktasiDTO(
                gun=satir["gun"],
                kayit_sayisi=int(satir["kayit_sayisi"]),
                toplam_adet=toplam_adet,
                saglam_adet=saglam_adet,
                fire_orani=fire_orani(toplam_adet, saglam_adet),
                oee=oee.oee,
            ).model_dump()
        )
    return basari(noktalar, mesaj="Günlük üretim trendi")
