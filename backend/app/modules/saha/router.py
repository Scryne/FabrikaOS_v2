"""Saha modülü uçları (``/api/v1/saha``).

Cihaz yönetimi tenant-kapsamlı + RBAC korumalı (``saha:oku``/``saha:yaz``); yazma audit'lenir.
Ölçüm ingestion uçları (``/olcumler``) ``edge`` izniyle korunur.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari, sayfali
from app.ingestion.service import IngestSonuc, olcum_yaz_toplu
from app.kimlik.models import Kullanici
from app.modules.saha import repository
from app.modules.saha.csv_ice import CsvGecersiz, csv_satirlari_coz
from app.modules.saha.models import AlinanOlcum, Cihaz
from app.modules.saha.schemas import (
    CihazCevapDTO,
    CihazOlusturDTO,
    OlcumKabulDTO,
    OlcumPaketi,
    SahaOzetDTO,
    SahaSayiDTO,
)

router = APIRouter(prefix="/saha", tags=["Saha"], dependencies=[Depends(modul_gerekli("saha"))])


def _cihaz_cevap(c: Cihaz) -> dict[str, Any]:
    return CihazCevapDTO(
        id=c.id, kod=c.kod, ad=c.ad, protokol=c.protokol, aktif=c.aktif, son_gorulme=c.son_gorulme
    ).model_dump()


# --- Cihaz yönetimi ---
@router.post(
    "/cihazlar", response_model=Zarf[CihazCevapDTO], status_code=201, summary="Saha cihazı oluştur"
)
async def cihaz_olustur(
    govde: CihazOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("saha:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    if await repository.cihaz_kod_var_mi(db, govde.kod):
        raise CakismaHatasi("Bu kod ile cihaz zaten var")
    cihaz = await repository.cihaz_ekle(
        db, Cihaz(kod=govde.kod, ad=govde.ad, protokol=govde.protokol)
    )
    await denetim_yaz(
        db, eylem="olustur", kaynak="saha_cihaz", kaynak_id=str(cihaz.id), kullanici=kullanici
    )
    return basari(_cihaz_cevap(cihaz), mesaj="Cihaz oluşturuldu")


@router.get("/cihazlar", response_model=Zarf[list[CihazCevapDTO]], summary="Cihazları listele")
async def cihaz_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("saha:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.cihaz_listele(
        db, sayfa=sayfa, adet=adet, arama=arama, siralama=siralama, yon=yon
    )
    return sayfali([_cihaz_cevap(c) for c in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/cihazlar/{cihaz_id}", response_model=Zarf[CihazCevapDTO], summary="Cihaz detayı")
async def cihaz_detay(
    cihaz_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("saha:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    cihaz = await repository.cihaz_getir(db, cihaz_id)
    if cihaz is None:
        raise KaynakBulunamadi("Cihaz bulunamadı")
    return basari(_cihaz_cevap(cihaz), mesaj="Cihaz detayı")


# --- Ölçüm ingestion (REST + CSV) ---
async def _yaz_ve_yayinla(
    db: AsyncSession, tenant: Tenant, cihaz_kod: str, paketler: list[OlcumPaketi]
) -> dict[str, Any]:
    sonuc: IngestSonuc = await olcum_yaz_toplu(db, cihaz_kod=cihaz_kod, paketler=paketler)
    for makine_id in sonuc.etkilenen_makineler:
        await yayinla(
            tenant.slug, {"tur": "uretim.eklendi", "makine_id": makine_id, "kaynak": "saha"}
        )
    return {
        "yazilan": sonuc.yazilan,
        "atlanan": sonuc.atlanan,
        "hatali": sonuc.hatali,
        "hatalar": list(sonuc.hatalar),
    }


@router.post(
    "/olcumler",
    response_model=Zarf[dict[str, Any]],
    status_code=201,
    summary="Saha ölçümü gönder",
)
async def olcum_gonder(
    govde: OlcumKabulDTO,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("edge"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    veri = await _yaz_ve_yayinla(db, tenant, govde.cihaz_kod, list(govde.olcumler))
    return basari(veri, mesaj="Ölçümler alındı")


@router.post(
    "/olcumler/csv",
    response_model=Zarf[dict[str, Any]],
    status_code=201,
    summary="CSV ile ölçüm yükle",
)
async def olcum_csv(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("edge"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    cihaz_kod: Annotated[str, Query(min_length=1, max_length=50)],
    dosya: Annotated[UploadFile, File()],
) -> dict[str, Any]:
    ham = (await dosya.read()).decode("utf-8-sig")
    try:
        paketler = csv_satirlari_coz(ham, cihaz_kod=cihaz_kod)
    except CsvGecersiz as exc:
        raise DogrulamaHatasi(str(exc)) from exc
    veri = await _yaz_ve_yayinla(db, tenant, cihaz_kod, paketler)
    return basari(veri, mesaj="CSV ölçümleri alındı")


@router.get("/ozet", response_model=Zarf[SahaOzetDTO], summary="Saha cihaz özeti (KPI)")
async def saha_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("saha:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    simdi = datetime.now(UTC)
    esik = simdi - timedelta(minutes=5)
    gun_basi = simdi.replace(hour=0, minute=0, second=0, microsecond=0)

    toplam = await db.scalar(select(func.count()).select_from(Cihaz)) or 0
    cevrimici = (
        await db.scalar(select(func.count()).select_from(Cihaz).where(Cihaz.son_gorulme >= esik))
        or 0
    )
    bugun_olcum = (
        await db.scalar(
            select(func.count())
            .select_from(AlinanOlcum)
            .where(AlinanOlcum.alinma_zamani >= gun_basi)
        )
        or 0
    )
    protokol_sonuc = await db.execute(select(Cihaz.protokol, func.count()).group_by(Cihaz.protokol))
    protokol_dagilimi = [SahaSayiDTO(ad=p, adet=int(a)) for p, a in protokol_sonuc.all()]

    ozet = SahaOzetDTO(
        toplam_cihaz=int(toplam),
        cevrimici=int(cevrimici),
        bugun_olcum=int(bugun_olcum),
        protokol_dagilimi=protokol_dagilimi,
    )
    return basari(ozet.model_dump(), mesaj="Saha özeti")
