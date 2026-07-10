"""Platform yönetim uçları: ``/api/v1/platform/*`` (kimlik hariç).

Tüm uçlar ``mevcut_platform_yonetici`` korumalıdır; tenant çözümlemesi YOKTUR
(control-plane istisnası — tenant-rbac-conventions). Yazma işlemleri
``platform_denetim_izi``'ne kaydedilir.
"""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Abonelik, Plan, PlatformYonetici, Tenant, TenantIhrac
from app.core.db.session import get_session
from app.core.exceptions import CakismaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.platform import ihrac as ihrac_mod
from app.platform import service
from app.platform.denetim import platform_denetim_yaz
from app.platform.deps import mevcut_platform_yonetici
from app.platform.schemas import (
    AbonelikSatirDTO,
    HakAyarlaDTO,
    IhracCevapDTO,
    ModulDurumDTO,
    OzellikDurumDTO,
    PlanSatirDTO,
    PlatformSaglikDTO,
    TenantDetayDTO,
    TenantGuncelleDTO,
    TenantOzetDTO,
    TenantProvizyonDTO,
    TenantSilDTO,
)

router = APIRouter(prefix="/platform", tags=["Platform"])


@router.get("/tenantlar", response_model=Zarf[list[TenantOzetDTO]], summary="Tenant'ları listele")
async def tenantlari_listele(
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
    arama: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await service.tenant_listele(db, sayfa=sayfa, adet=adet, arama=arama)
    return sayfali([k.model_dump() for k in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.post(
    "/tenantlar",
    response_model=Zarf[TenantDetayDTO],
    status_code=201,
    summary="Tenant provizyonla",
)
async def tenant_provizyonla_uc(
    govde: TenantProvizyonDTO,
    yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    tenant = await service.tenant_provizyon(db, yonetici, govde)
    detay = await service.tenant_detayi(db, tenant)
    return basari(detay.model_dump(), mesaj="Tenant provizyonlandı")


@router.patch(
    "/tenantlar/{tenant_id}", response_model=Zarf[TenantDetayDTO], summary="Tenant güncelle"
)
async def tenant_guncelle_uc(
    tenant_id: int,
    govde: TenantGuncelleDTO,
    yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    tenant = await service.tenant_guncelle(db, yonetici, tenant_id, govde)
    detay = await service.tenant_detayi(db, tenant)
    return basari(detay.model_dump(), mesaj="Tenant güncellendi")


@router.post(
    "/tenantlar/{tenant_id}/askiya-al",
    response_model=Zarf[TenantDetayDTO],
    summary="Tenant'ı askıya al",
)
async def tenant_askiya_al(
    tenant_id: int,
    yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    tenant = await service.tenant_aktiflik_ayarla(db, yonetici, tenant_id, aktif=False)
    detay = await service.tenant_detayi(db, tenant)
    return basari(detay.model_dump(), mesaj="Tenant askıya alındı")


@router.post(
    "/tenantlar/{tenant_id}/aktiflestir",
    response_model=Zarf[TenantDetayDTO],
    summary="Tenant'ı aktifleştir",
)
async def tenant_aktiflestir(
    tenant_id: int,
    yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    tenant = await service.tenant_aktiflik_ayarla(db, yonetici, tenant_id, aktif=True)
    detay = await service.tenant_detayi(db, tenant)
    return basari(detay.model_dump(), mesaj="Tenant aktifleştirildi")


@router.delete(
    "/tenantlar/{tenant_id}", response_model=Zarf[None], summary="Tenant'ı sil (geri dönüşsüz)"
)
async def tenant_sil_uc(
    tenant_id: int,
    govde: TenantSilDTO,
    yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    await service.tenant_sil(db, yonetici, tenant_id, onay=govde.onay)
    return basari(None, mesaj="Tenant silindi")


@router.get("/tenantlar/{tenant_id}", response_model=Zarf[TenantDetayDTO], summary="Tenant detayı")
async def tenant_detay(
    tenant_id: int,
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    tenant = await service.tenant_getir(db, tenant_id)
    detay = await service.tenant_detayi(db, tenant)
    return basari(detay.model_dump(), mesaj="Tenant detayı")


@router.put(
    "/tenantlar/{tenant_id}/modul-haklari/{modul_kodu}",
    response_model=Zarf[list[ModulDurumDTO]],
    summary="Modül hakkını ayarla (null = plana dön)",
)
async def modul_hakki_ayarla_uc(
    tenant_id: int,
    modul_kodu: str,
    govde: HakAyarlaDTO,
    yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    moduller = await service.modul_hakki_yaz(db, yonetici, tenant_id, modul_kodu, govde.acik)
    return basari([m.model_dump() for m in moduller], mesaj="Modül hakkı güncellendi")


@router.put(
    "/tenantlar/{tenant_id}/ozellik-bayraklari/{kod}",
    response_model=Zarf[list[OzellikDurumDTO]],
    summary="Özellik bayrağını ayarla (null = plana dön)",
)
async def ozellik_bayragi_ayarla_uc(
    tenant_id: int,
    kod: str,
    govde: HakAyarlaDTO,
    yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    ozellikler = await service.ozellik_bayragi_yaz(db, yonetici, tenant_id, kod, govde.acik)
    return basari([o.model_dump() for o in ozellikler], mesaj="Özellik bayrağı güncellendi")


@router.get(
    "/abonelikler", response_model=Zarf[list[AbonelikSatirDTO]], summary="Abonelikleri listele"
)
async def abonelikleri_listele(
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    toplam = await db.scalar(select(func.count()).select_from(Abonelik)) or 0
    sonuc = await db.execute(
        select(Abonelik, Tenant)
        .join(Tenant, Abonelik.tenant_id == Tenant.id)
        .order_by(Abonelik.id.desc())
        .offset((sayfa - 1) * adet)
        .limit(adet)
    )
    kayitlar = [
        AbonelikSatirDTO(
            id=ab.id,
            tenant_id=t.id,
            tenant_slug=t.slug,
            tenant_ad=t.ad,
            plan_kodu=ab.plan_kodu,
            durum=ab.durum,
            baslangic_tarihi=ab.baslangic_tarihi,
            bitis_tarihi=ab.bitis_tarihi,
        ).model_dump()
        for ab, t in sonuc.all()
    ]
    return sayfali(kayitlar, sayfa=sayfa, adet=adet, toplam=int(toplam))


def _ihrac_cevap(k: TenantIhrac) -> dict[str, Any]:
    return IhracCevapDTO(
        id=k.id,
        tenant_id=k.tenant_id,
        slug=k.slug,
        durum=k.durum,
        boyut=k.boyut,
        tablo_sayisi=k.tablo_sayisi,
        hata=k.hata,
        olusturan_eposta=k.olusturan_eposta,
        olusturma_tarihi=k.olusturma_tarihi,
    ).model_dump()


@router.post(
    "/tenantlar/{tenant_id}/ihrac",
    response_model=Zarf[IhracCevapDTO],
    status_code=202,
    summary="KVKK veri ihracını başlat (arka plan)",
)
async def ihrac_baslat(
    tenant_id: int,
    yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    tenant = await service.tenant_getir(db, tenant_id)
    kayit = TenantIhrac(tenant_id=tenant.id, slug=tenant.slug, olusturan_eposta=yonetici.eposta)
    db.add(kayit)
    await db.flush()
    await platform_denetim_yaz(
        db,
        eylem="ihrac",
        kaynak="tenant",
        kaynak_id=str(tenant.id),
        yonetici=yonetici,
        detay={"slug": tenant.slug, "ihrac_id": kayit.id},
    )
    cevap = _ihrac_cevap(kayit)  # "kuyrukta" anlık görüntüsü
    # Arka plan görevi kaydı kendi oturumundan okuyacak → önce kalıcı olmalı.
    await db.commit()
    await ihrac_mod.uretim_planla(kayit.id)
    return basari(cevap, mesaj="İhraç başlatıldı")


@router.get("/ihraclar", response_model=Zarf[list[IhracCevapDTO]], summary="İhraçları listele")
async def ihraclari_listele(
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
    tenant_id: int | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    sorgu = select(TenantIhrac)
    if tenant_id is not None:
        sorgu = sorgu.where(TenantIhrac.tenant_id == tenant_id)
    toplam = await db.scalar(select(func.count()).select_from(sorgu.subquery())) or 0
    sonuc = await db.execute(
        sorgu.order_by(TenantIhrac.id.desc()).offset((sayfa - 1) * adet).limit(adet)
    )
    kayitlar = [_ihrac_cevap(k) for k in sonuc.scalars()]
    return sayfali(kayitlar, sayfa=sayfa, adet=adet, toplam=int(toplam))


@router.get("/ihraclar/{ihrac_id}/indir", summary="Hazır ihracı indir (ZIP)")
async def ihrac_indir(
    ihrac_id: int,
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Response:
    kayit = await db.get(TenantIhrac, ihrac_id)
    if kayit is None:
        raise KaynakBulunamadi("İhraç kaydı bulunamadı")
    if kayit.durum != "hazir":
        raise CakismaHatasi(f"İhraç indirilebilir durumda değil (durum: {kayit.durum})")
    veri = await ihrac_mod.ihrac_icerik_indir(kayit)
    dosya = quote(f"tenant-{kayit.slug}-ihrac-{kayit.id}.zip")
    return Response(
        content=veri,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{dosya}"},
    )


@router.get("/planlar", response_model=Zarf[list[PlanSatirDTO]], summary="Plan kataloğu")
async def planlari_listele(
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    sonuc = await db.execute(select(Plan).where(Plan.aktif).order_by(Plan.id))
    kayitlar = [
        PlanSatirDTO(
            kod=p.kod,
            ad=p.ad,
            koltuk_limiti=p.koltuk_limiti,
            moduller=list(p.moduller),
            ozellikler=list(p.ozellikler),
        ).model_dump()
        for p in sonuc.scalars()
    ]
    return basari(kayitlar, mesaj="Plan kataloğu")


@router.get("/saglik", response_model=Zarf[PlatformSaglikDTO], summary="Platform sağlığı")
async def platform_sagligi(
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    durum = await service.saglik_durumu(db)
    return basari(durum.model_dump(), mesaj="Platform sağlığı")
