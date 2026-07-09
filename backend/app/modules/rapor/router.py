"""Rapor uçları (``/api/v1/raporlar``) — async üretim (202) + liste/detay/indir.

Tüm uçlar tenant-kapsamlı + RBAC: görüntüleme/indirme ``rapor:oku``, oluşturma
``rapor:yaz`` (görev ayrımı — izleyici raporu okur ama üretemez). ``POST /raporlar``
kaydı commit ettikten sonra arka plan görevini planlar ve **202** döner; durum
liste/detay üzerinden (veya ``rapor.hazir`` gerçek-zaman olayıyla) izlenir.
"""

from __future__ import annotations

from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.rapor import repository, service
from app.modules.rapor.birimler import RAPOR_DURUMLARI
from app.modules.rapor.models import Rapor
from app.modules.rapor.schemas import RaporCevapDTO, RaporOlusturDTO

router = APIRouter(
    prefix="/raporlar", tags=["Rapor"], dependencies=[Depends(modul_gerekli("rapor"))]
)


def _cevap(r: Rapor) -> dict[str, Any]:
    return RaporCevapDTO(
        id=r.id,
        kod=r.kod,
        tur=r.tur,
        bicim=r.bicim,
        durum=r.durum,
        parametreler=r.parametreler,
        dosya_adi=r.dosya_adi,
        icerik_tipi=r.icerik_tipi,
        boyut=r.boyut,
        satir_sayisi=r.satir_sayisi,
        hata=r.hata,
        uretim_suresi_sn=r.uretim_suresi_sn,
        olusturan_kullanici_id=r.olusturan_kullanici_id,
        olusturma_tarihi=r.olusturma_tarihi,
    ).model_dump()


@router.post(
    "",
    response_model=Zarf[RaporCevapDTO],
    status_code=202,
    summary="Rapor üretimini başlat (arka plan)",
)
async def rapor_olustur(
    govde: RaporOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("rapor:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kayit = await service.rapor_olustur(
        db, tur=govde.tur, bicim=govde.bicim, gun=govde.gun, kullanici_id=kullanici.id
    )
    await denetim_yaz(
        db,
        eylem="olustur",
        kaynak="rapor",
        kaynak_id=str(kayit.id),
        kullanici=kullanici,
        detay={"tur": kayit.tur, "bicim": kayit.bicim, "kod": kayit.kod},
    )
    cevap = _cevap(kayit)  # "kuyrukta" anlık görüntüsü (görev sonucu beklenmez)
    # Arka plan görevi kaydı kendi oturumundan okuyacak → önce kalıcı olmalı.
    await db.commit()
    await service.uretim_planla(kayit.id, tenant.slug)
    return basari(cevap, mesaj="Rapor üretimi başlatıldı")


@router.get("", response_model=Zarf[list[RaporCevapDTO]], summary="Raporları listele")
async def rapor_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("rapor:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    tur: str | None = None,
    durum: str | None = None,
) -> dict[str, Any]:
    if tur is not None:
        service.tur_dogrula(tur)
    if durum is not None and durum not in RAPOR_DURUMLARI:
        raise DogrulamaHatasi(
            "Geçersiz rapor durumu",
            detaylar=[
                {"alan": "durum", "mesaj": f"şunlardan biri olmalı: {sorted(RAPOR_DURUMLARI)}"}
            ],
        )
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.rapor_listele(
        db, sayfa=sayfa, adet=adet, tur=tur, durum=durum
    )
    return sayfali([_cevap(r) for r in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/{rapor_id}", response_model=Zarf[RaporCevapDTO], summary="Rapor detayı")
async def rapor_detay(
    rapor_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("rapor:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kayit = await repository.rapor_getir(db, rapor_id)
    if kayit is None:
        raise KaynakBulunamadi("Rapor bulunamadı")
    return basari(_cevap(kayit), mesaj="Rapor detayı")


@router.get("/{rapor_id}/indir", summary="Hazır raporu indir (ikili içerik)")
async def rapor_indir(
    rapor_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("rapor:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> Response:
    kayit = await repository.rapor_getir(db, rapor_id)
    if kayit is None:
        raise KaynakBulunamadi("Rapor bulunamadı")
    if kayit.durum != "hazir":
        raise CakismaHatasi(f"Rapor indirilebilir durumda değil (durum: {kayit.durum})")
    veri = await service.rapor_icerik_indir(kayit)
    dosya = quote(kayit.dosya_adi)
    return Response(
        content=veri,
        media_type=kayit.icerik_tipi,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{dosya}"},
    )
