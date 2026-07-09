"""Enerji uçları (``/api/v1``) — tüketim ölçümü + continuous aggregate trend.

Tenant-kapsamlı + RBAC (``enerji:oku``/``enerji:yaz``); yazma audit'lenir.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.enerji import repository, service
from app.modules.enerji.birimler import ENERJI_TURLERI
from app.modules.enerji.models import EnerjiTuketim
from app.modules.enerji.schemas import (
    EnerjiOlcumCevapDTO,
    EnerjiOlcumOlusturDTO,
    EnerjiOzetDTO,
    EnerjiTrendNoktaDTO,
)

router = APIRouter(tags=["Enerji"], dependencies=[Depends(modul_gerekli("enerji"))])

# Trend granülerlik beyaz-listesi (SQL enjeksiyonuna karşı; geçersiz → varsayılan 'saat').
_ARALIKLAR = frozenset({"saat", "gun"})


def _olcum_cevap(o: EnerjiTuketim) -> dict[str, Any]:
    return EnerjiOlcumCevapDTO(
        id=o.id,
        makine_id=o.makine_id,
        enerji_turu=o.enerji_turu,
        tuketim=float(o.tuketim),
        birim=o.birim,
        zaman=o.zaman,
    ).model_dump()


@router.post(
    "/enerji-tuketimleri",
    response_model=Zarf[EnerjiOlcumCevapDTO],
    status_code=201,
    summary="Enerji tüketim ölçümü ekle",
)
async def olcum_olustur(
    govde: EnerjiOlcumOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("enerji:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if govde.enerji_turu not in ENERJI_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz enerji türü",
            detaylar=[
                {"alan": "enerji_turu", "mesaj": f"Geçerli: {', '.join(sorted(ENERJI_TURLERI))}"}
            ],
        )
    olcum = await service.olcum_yaz(
        db,
        makine_id=govde.makine_id,
        enerji_turu=govde.enerji_turu,
        tuketim=govde.tuketim,
        birim=govde.birim,
        zaman=govde.zaman,
    )
    await denetim_yaz(
        db, eylem="olustur", kaynak="enerji_tuketim", kaynak_id=str(olcum.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "enerji.olcum", "makine_id": olcum.makine_id})
    return basari(_olcum_cevap(olcum), mesaj="Enerji ölçümü eklendi")


@router.get(
    "/enerji-tuketimleri",
    response_model=Zarf[list[EnerjiOlcumCevapDTO]],
    summary="Enerji tüketim ölçümlerini listele",
)
async def olcum_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("enerji:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    makine_id: int | None = None,
    enerji_turu: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.olcum_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        makine_id=makine_id,
        enerji_turu=enerji_turu,
        baslangic=baslangic,
        bitis=bitis,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_olcum_cevap(o) for o in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/enerji-tuketimleri/trend",
    response_model=Zarf[list[EnerjiTrendNoktaDTO]],
    summary="Enerji tüketim trendi (continuous aggregate)",
)
async def enerji_trend(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("enerji:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    makine_id: int | None = None,
    enerji_turu: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    aralik: str = "saat",
) -> dict[str, Any]:
    if aralik not in _ARALIKLAR:
        aralik = "saat"
    noktalar = await repository.trend(
        db,
        makine_id=makine_id,
        enerji_turu=enerji_turu,
        baslangic=baslangic,
        bitis=bitis,
        aralik=aralik,
    )
    return basari([EnerjiTrendNoktaDTO(**n).model_dump() for n in noktalar], mesaj="Enerji trendi")


@router.get("/enerji/ozet", response_model=Zarf[EnerjiOzetDTO], summary="Enerji özeti (KPI)")
async def enerji_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("enerji:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    gun_basi = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    toplam = await db.scalar(select(func.count()).select_from(EnerjiTuketim)) or 0
    bugun = (
        await db.scalar(
            select(func.count()).select_from(EnerjiTuketim).where(EnerjiTuketim.zaman >= gun_basi)
        )
        or 0
    )
    tur_sayisi = await db.scalar(select(func.count(func.distinct(EnerjiTuketim.enerji_turu)))) or 0
    izlenen_makine = (
        await db.scalar(
            select(func.count(func.distinct(EnerjiTuketim.makine_id))).where(
                EnerjiTuketim.makine_id.is_not(None)
            )
        )
        or 0
    )

    ozet = EnerjiOzetDTO(
        toplam_kayit=int(toplam),
        bugun_kayit=int(bugun),
        tur_sayisi=int(tur_sayisi),
        izlenen_makine=int(izlenen_makine),
    )
    return basari(ozet.model_dump(), mesaj="Enerji özeti")
