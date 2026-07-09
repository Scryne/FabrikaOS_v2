"""AI tahmin uçları (``/api/v1/tahmin``) — eğitim tetikleme + dört çıkarım ucu.

Tüm uçlar tenant-kapsamlı + RBAC: çıkarım/görüntüleme ``ai:oku``, eğitim ``ai:egit``
(görev ayrımı — izleyici tahmin okur ama model eğitemez). ``POST /tahmin/egit``
kaydı commit ettikten sonra arka plan görevini planlar ve **202** döner; durum
``GET /tahmin/modeller`` üzerinden (veya ``ai.model`` gerçek-zaman olayıyla) izlenir.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.ai import repository, service
from app.modules.ai.models import ModelKaydi
from app.modules.ai.schemas import (
    EgitimIstekDTO,
    ModelKaydiCevapDTO,
    TahminCevapDTO,
    TahminGecmisCevapDTO,
)

router = APIRouter(
    prefix="/tahmin", tags=["AI Tahmin"], dependencies=[Depends(modul_gerekli("ai"))]
)


def _kayit_cevap(k: ModelKaydi) -> dict[str, Any]:
    return ModelKaydiCevapDTO(
        id=k.id,
        tur=k.tur,
        surum=k.surum,
        durum=k.durum,
        aktif=k.aktif,
        metrikler=k.metrikler,
        veri_ozeti=k.veri_ozeti,
        hata=k.hata,
        egitim_suresi_sn=k.egitim_suresi_sn,
        olusturan_kullanici_id=k.olusturan_kullanici_id,
        olusturma_tarihi=k.olusturma_tarihi,
    ).model_dump()


@router.get(
    "/modeller",
    response_model=Zarf[list[ModelKaydiCevapDTO]],
    summary="Model kayıtlarını listele",
)
async def model_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("ai:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    tur: str | None = None,
) -> dict[str, Any]:
    if tur is not None:
        service.tur_dogrula(tur)
    kayitlar = await repository.kayit_listele(db, tur=tur)
    return basari([_kayit_cevap(k) for k in kayitlar], mesaj="Model kayıtları")


@router.post(
    "/egit",
    response_model=Zarf[ModelKaydiCevapDTO],
    status_code=202,
    summary="Model eğitimini başlat (arka plan)",
)
async def egitim_baslat(
    govde: EgitimIstekDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ai:egit"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kayit = await service.egitim_baslat(db, tur=govde.tur, kullanici_id=kullanici.id)
    await denetim_yaz(
        db,
        eylem="egit",
        kaynak="ai_model",
        kaynak_id=str(kayit.id),
        kullanici=kullanici,
        detay={"tur": kayit.tur, "surum": kayit.surum},
    )
    cevap = _kayit_cevap(kayit)  # "egitiliyor" anlık görüntüsü (görev sonucu beklenmez)
    # Arka plan görevi kaydı kendi oturumundan okuyacak → önce kalıcı olmalı.
    await db.commit()
    await service.egitim_planla(kayit.id, tenant.slug, kayit.tur)
    return basari(cevap, mesaj="Eğitim başlatıldı")


@router.get(
    "/gecmis",
    response_model=Zarf[list[TahminGecmisCevapDTO]],
    summary="Tahmin geçmişini listele",
)
async def tahmin_gecmisi(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("ai:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    tur: str | None = None,
) -> dict[str, Any]:
    if tur is not None:
        service.tur_dogrula(tur)
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.tahmin_listele(db, tur=tur, sayfa=sayfa, adet=adet)
    veri = [
        TahminGecmisCevapDTO(
            id=t.id,
            tur=t.tur,
            model_id=t.model_id,
            sonuc_sayisi=len(t.cikti) if isinstance(t.cikti, list) else 0,
            veri_ozeti=t.veri_ozeti,
            olusturma_tarihi=t.olusturma_tarihi,
        ).model_dump()
        for t in kayitlar
    ]
    return sayfali(veri, sayfa=sayfa, adet=adet, toplam=toplam)


async def _tahmin_ucu(
    tur: str, kullanici: Kullanici, db: AsyncSession, tenant: Tenant
) -> dict[str, Any]:
    cikarim = await service.tahmin_calistir(
        db, slug=tenant.slug, tur=tur, kullanici_id=kullanici.id
    )
    await denetim_yaz(
        db,
        eylem="tahmin",
        kaynak="ai_tahmin",
        kaynak_id=str(cikarim.tahmin.id),
        kullanici=kullanici,
        detay={"tur": tur, "model_surum": cikarim.kayit.surum},
    )
    veri = TahminCevapDTO(
        tahmin_id=cikarim.tahmin.id,
        tur=tur,
        model_id=cikarim.kayit.id,
        model_surum=cikarim.kayit.surum,
        sonuclar=cikarim.sonuclar,
        veri_ozeti=cikarim.tahmin.veri_ozeti,
        zaman=cikarim.tahmin.olusturma_tarihi,
    ).model_dump()
    return basari(veri, mesaj="Tahmin üretildi")


@router.get(
    "/kestirimci-bakim",
    response_model=Zarf[TahminCevapDTO],
    summary="Kestirimci bakım riski (makine başına)",
)
async def kestirimci_bakim_tahmini(
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ai:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _tahmin_ucu("kestirimci_bakim", kullanici, db, tenant)


@router.get(
    "/oee",
    response_model=Zarf[TahminCevapDTO],
    summary="OEE ufuk tahmini (makine başına)",
)
async def oee_tahmini(
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ai:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _tahmin_ucu("oee", kullanici, db, tenant)


@router.get(
    "/stok",
    response_model=Zarf[TahminCevapDTO],
    summary="Stok ihtiyaç tahmini (malzeme başına kalan gün)",
)
async def stok_tahmini(
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ai:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _tahmin_ucu("stok", kullanici, db, tenant)


@router.get(
    "/anomali",
    response_model=Zarf[TahminCevapDTO],
    summary="Anomali taraması (son gözlem penceresi)",
)
async def anomali_tahmini(
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ai:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _tahmin_ucu("anomali", kullanici, db, tenant)
