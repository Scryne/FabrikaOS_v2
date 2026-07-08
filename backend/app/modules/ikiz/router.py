"""Dijital ikiz uçları (``/api/v1/ikiz``).

- ``GET/PUT /ikiz/yerlesim`` — tesis şeması düğümleri (``uretim:oku`` / ``uretim:yaz``).
  PUT **replace-all** (idempotent); başarıda best-effort ``ikiz.yerlesim`` gerçek-zaman
  yayını (outbox yok — UI kaygısı, ADR-0017).
- ``GET /ikiz/durum`` — yerleşim ⋈ makine canlı durumu + pencere OEE/üretim özeti;
  kiosk büyük ekranının tek veri kaynağı (``uretim:oku``).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari
from app.kimlik.models import Kullanici
from app.modules.analitik.hesap import donem_oee, fire_orani
from app.modules.ikiz import repository
from app.modules.ikiz.models import IkizDugum
from app.modules.ikiz.schemas import (
    IkizDugumCevapDTO,
    IkizDugumDurumDTO,
    IkizDurumCevapDTO,
    IkizOzetDTO,
    YerlesimKaydetDTO,
    YerlesmemisMakineDTO,
)
from app.modules.uretim.models import Makine

router = APIRouter(prefix="/ikiz", tags=["Dijital İkiz"])

_SaatParam = Annotated[int, Query(ge=1, le=168, description="Geriye dönük pencere (saat)")]


def _dugum_cevap(d: IkizDugum) -> dict[str, Any]:
    return IkizDugumCevapDTO(
        id=d.id, makine_id=d.makine_id, x=d.x, y=d.y, bolge=d.bolge
    ).model_dump()


@router.get(
    "/yerlesim",
    response_model=Zarf[list[IkizDugumCevapDTO]],
    summary="İkiz yerleşimini getir",
)
async def yerlesim_getir(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    dugumler = await repository.dugumleri_getir(db)
    return basari([_dugum_cevap(d) for d in dugumler], mesaj="İkiz yerleşimi")


@router.put(
    "/yerlesim",
    response_model=Zarf[list[IkizDugumCevapDTO]],
    summary="İkiz yerleşimini kaydet (replace-all)",
)
async def yerlesim_kaydet(
    govde: YerlesimKaydetDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    makine_idler = [d.makine_id for d in govde.dugumler]
    if len(makine_idler) != len(set(makine_idler)):
        raise DogrulamaHatasi(
            "Bir makine şemada en fazla bir kez yer alabilir",
            detaylar=[{"alan": "dugumler", "mesaj": "mükerrer makine_id"}],
        )
    mevcut = await repository.makine_id_kumesi(db)
    bilinmeyen = sorted(set(makine_idler) - mevcut)
    if bilinmeyen:
        raise DogrulamaHatasi(
            "Bilinmeyen makine",
            detaylar=[
                {"alan": "dugumler", "mesaj": f"makine_id bulunamadı: {mid}"} for mid in bilinmeyen
            ],
        )
    dugumler = await repository.yerlesimi_degistir(db, [d.model_dump() for d in govde.dugumler])
    await denetim_yaz(
        db,
        eylem="yerlesim_guncelle",
        kaynak="ikiz",
        kaynak_id="yerlesim",
        kullanici=kullanici,
        detay={"dugum_sayisi": len(dugumler)},
    )
    await yayinla(tenant.slug, {"tur": "ikiz.yerlesim"})
    return basari([_dugum_cevap(d) for d in dugumler], mesaj="Yerleşim kaydedildi")


@router.get(
    "/durum",
    response_model=Zarf[IkizDurumCevapDTO],
    summary="İkiz canlı durumu (yerleşim + makine durumu + pencere OEE)",
)
async def ikiz_durum(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    saat: _SaatParam = 24,
) -> dict[str, Any]:
    simdi = datetime.now(UTC)
    esik = simdi - timedelta(hours=saat)

    makineler = await repository.makineleri_getir(db)
    dugumler = await repository.dugumleri_getir(db)
    toplamlar = await repository.makine_pencere_toplamlari(db, esik=esik)
    acik_ariza = await repository.acik_ariza_sayisi(db)

    makine_haritasi: dict[int, Makine] = {m.id: m for m in makineler}
    yerlesik_idler = {d.makine_id for d in dugumler}

    dugum_cevaplari: list[IkizDugumDurumDTO] = []
    for d in dugumler:
        makine = makine_haritasi[d.makine_id]
        satir = toplamlar.get(d.makine_id)
        makine_oee = (
            donem_oee(
                planlanan_sure_dk=float(satir["planlanan"]),
                durus_sure_dk=float(satir["durus"]),
                toplam_adet=int(satir["toplam_adet"]),
                saglam_adet=int(satir["saglam_adet"]),
                ideal_toplam_sn=float(satir["ideal_toplam_sn"]),
            ).oee
            if satir is not None
            else None
        )
        dugum_cevaplari.append(
            IkizDugumDurumDTO(
                makine_id=d.makine_id,
                makine_kod=makine.kod,
                makine_ad=makine.ad,
                durum=makine.durum,
                x=d.x,
                y=d.y,
                bolge=d.bolge,
                oee=makine_oee,
                toplam_adet=int(satir["toplam_adet"]) if satir is not None else 0,
                son_veri_zamani=satir["son_veri_zamani"] if satir is not None else None,
            )
        )

    durumlar: dict[str, int] = {}
    for m in makineler:
        durumlar[m.durum] = durumlar.get(m.durum, 0) + 1

    toplam_adet = sum(int(s["toplam_adet"]) for s in toplamlar.values())
    saglam_adet = sum(int(s["saglam_adet"]) for s in toplamlar.values())
    tesis_oee = donem_oee(
        planlanan_sure_dk=sum(float(s["planlanan"]) for s in toplamlar.values()),
        durus_sure_dk=sum(float(s["durus"]) for s in toplamlar.values()),
        toplam_adet=toplam_adet,
        saglam_adet=saglam_adet,
        ideal_toplam_sn=sum(float(s["ideal_toplam_sn"]) for s in toplamlar.values()),
    )

    cevap = IkizDurumCevapDTO(
        saat=saat,
        baslangic=esik,
        bitis=simdi,
        ozet=IkizOzetDTO(
            toplam_makine=len(makineler),
            durumlar=durumlar,
            kayit_sayisi=sum(int(s["kayit_sayisi"]) for s in toplamlar.values()),
            toplam_adet=toplam_adet,
            saglam_adet=saglam_adet,
            fire_orani=fire_orani(toplam_adet, saglam_adet),
            oee=tesis_oee.oee,
            acik_ariza=acik_ariza,
        ),
        dugumler=dugum_cevaplari,
        yerlesmemis=[
            YerlesmemisMakineDTO(makine_id=m.id, makine_kod=m.kod, makine_ad=m.ad, durum=m.durum)
            for m in makineler
            if m.id not in yerlesik_idler
        ],
    )
    return basari(cevap.model_dump(), mesaj="İkiz durumu")
