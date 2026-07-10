"""Dış veri uçları (``/api/v1/entegrasyon/*``) — 3. taraf ERP/muhasebe erişimi.

Kimlik JWT değil **API anahtarıdır** (``X-API-Anahtar`` + ``X-Tenant``): her uç
``api_izin_gerekli("<kapsam>")`` ile korunur; anahtarın ``izinler`` listesi kapsamı
içermiyorsa 403. Salt-okunur yüzeydir; iç RBAC zincirine dokunmaz (JWT uçları
etkilenmez). Sıkı modül kapısı ``modul_gerekli("entegrasyon")``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db.session import get_session
from app.core.deps import modul_gerekli
from app.core.responses import Zarf, basari, sayfali
from app.modules.entegrasyon.deps import api_izin_gerekli
from app.modules.entegrasyon.models import ApiAnahtari
from app.modules.entegrasyon.schemas import (
    SatinalmaKalemiDisDTO,
    SatinalmaTalebiDisDTO,
    StokBakiyeDTO,
    UretimOzetiSatirDTO,
)
from app.modules.stok.models import Malzeme, SatinalmaTalebi
from app.modules.stok.talep_durum import DURUMLAR as TALEP_DURUMLARI
from app.modules.uretim import repository as uretim_repository
from app.modules.uretim.service import oee_toplamdan

router = APIRouter(
    prefix="/entegrasyon",
    tags=["Entegrasyon"],
    dependencies=[Depends(modul_gerekli("entegrasyon"))],
)


@router.get(
    "/stok-bakiyeleri",
    response_model=Zarf[list[StokBakiyeDTO]],
    summary="Stok bakiyeleri (API anahtarı; kapsam stok:oku)",
)
async def stok_bakiyeleri(
    _anahtar: Annotated[ApiAnahtari, Depends(api_izin_gerekli("stok:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 100,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 500)
    sorgu = select(Malzeme).where(Malzeme.aktif)
    toplam = (await db.execute(select(func.count()).select_from(sorgu.subquery()))).scalar_one()
    sonuc = await db.execute(sorgu.order_by(Malzeme.kod).offset((sayfa - 1) * adet).limit(adet))
    satirlar = [
        StokBakiyeDTO(
            malzeme_id=m.id,
            kod=m.kod,
            ad=m.ad,
            birim=m.birim,
            kategori=m.kategori,
            mevcut_miktar=float(m.mevcut_miktar),
            kritik_stok=float(m.kritik_stok),
            kritik_altinda=m.mevcut_miktar <= m.kritik_stok,
        ).model_dump()
        for m in sonuc.scalars()
    ]
    return sayfali(satirlar, sayfa=sayfa, adet=adet, toplam=int(toplam))


@router.get(
    "/satinalma-talepleri",
    response_model=Zarf[list[SatinalmaTalebiDisDTO]],
    summary="Satınalma talepleri (API anahtarı; kapsam satinalma:oku)",
)
async def satinalma_talepleri(
    _anahtar: Annotated[ApiAnahtari, Depends(api_izin_gerekli("satinalma:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    durum: str = "onaylandi",
    sayfa: int = 1,
    adet: int = 50,
) -> dict[str, Any]:
    """Varsayılan ``durum=onaylandi``: ERP tarafında satınalma siparişine dönecek talepler."""
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 200)
    sorgu = select(SatinalmaTalebi)
    if durum in TALEP_DURUMLARI:
        sorgu = sorgu.where(SatinalmaTalebi.durum == durum)
    toplam = (await db.execute(select(func.count()).select_from(sorgu.subquery()))).scalar_one()
    sonuc = await db.execute(
        sorgu.options(selectinload(SatinalmaTalebi.kalemler))
        .order_by(SatinalmaTalebi.id.desc())
        .offset((sayfa - 1) * adet)
        .limit(adet)
    )
    satirlar = [
        SatinalmaTalebiDisDTO(
            id=t.id,
            kod=t.kod,
            baslik=t.baslik,
            durum=t.durum,
            para_birimi=t.para_birimi,
            onay_tarihi=t.onay_tarihi,
            olusturma_tarihi=t.olusturma_tarihi,
            kalemler=[
                SatinalmaKalemiDisDTO(
                    malzeme_id=k.malzeme_id,
                    miktar=float(k.miktar),
                    birim=k.birim,
                    tahmini_birim_fiyat=(
                        float(k.tahmini_birim_fiyat) if k.tahmini_birim_fiyat is not None else None
                    ),
                )
                for k in t.kalemler
            ],
        ).model_dump()
        for t in sonuc.scalars()
    ]
    return sayfali(satirlar, sayfa=sayfa, adet=adet, toplam=int(toplam))


@router.get(
    "/uretim-ozeti",
    response_model=Zarf[list[UretimOzetiSatirDTO]],
    summary="Günlük üretim özeti + OEE (API anahtarı; kapsam uretim:oku)",
)
async def uretim_ozeti(
    _anahtar: Annotated[ApiAnahtari, Depends(api_izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    gun: date | None = None,
) -> dict[str, Any]:
    """``gun`` (UTC, varsayılan bugün) için makine başına üretim/fire + OEE."""
    gun = gun or datetime.now(UTC).date()
    baslangic = datetime(gun.year, gun.month, gun.day, tzinfo=UTC)
    bitis = baslangic + timedelta(days=1)
    satirlar = await uretim_repository.oee_ozet(db, baslangic=baslangic, bitis=bitis)
    veri: list[dict[str, Any]] = []
    for makine_id, kod, toplam in satirlar:
        sonuc = oee_toplamdan(toplam)
        veri.append(
            UretimOzetiSatirDTO(
                makine_id=makine_id,
                makine_kod=kod,
                toplam_adet=toplam.toplam_adet,
                saglam_adet=toplam.saglam_adet,
                fire_adet=toplam.toplam_adet - toplam.saglam_adet,
                oee=sonuc.oee,
                kullanilabilirlik=sonuc.kullanilabilirlik,
                performans=sonuc.performans,
                kalite=sonuc.kalite,
            ).model_dump()
        )
    return basari(veri, mesaj=f"{gun.isoformat()} üretim özeti")
