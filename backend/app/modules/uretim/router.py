"""Üretim modülü uçları (``/api/v1``).

Tüm uçlar tenant-kapsamlı ve RBAC korumalı (``uretim:oku`` / ``uretim:yaz``).
Yazma işlemleri denetim izine kaydedilir.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.uretim import repository, service
from app.modules.uretim.models import MAKINE_DURUMLARI, Makine, UretimVerisi
from app.modules.uretim.schemas import (
    MakineCevapDTO,
    MakineDurumDTO,
    MakineOlusturDTO,
    OeeCevapDTO,
    OeeOzetSatirDTO,
    UretimGirisDTO,
    UretimVerisiCevapDTO,
)

router = APIRouter(tags=["Üretim"])


def _makine_cevap(m: Makine) -> dict[str, Any]:
    return MakineCevapDTO(
        id=m.id, kod=m.kod, ad=m.ad, durum=m.durum, oee_hedefi=m.oee_hedefi
    ).model_dump()


def _uretim_cevap(u: UretimVerisi) -> dict[str, Any]:
    return UretimVerisiCevapDTO(
        id=u.id,
        makine_id=u.makine_id,
        zaman=u.zaman,
        vardiya=u.vardiya,
        planlanan_sure_dk=u.planlanan_sure_dk,
        durus_sure_dk=u.durus_sure_dk,
        toplam_adet=u.toplam_adet,
        saglam_adet=u.saglam_adet,
        ideal_cevrim_sn=u.ideal_cevrim_sn,
    ).model_dump()


# --- Makineler ---
@router.post(
    "/makineler", response_model=Zarf[MakineCevapDTO], status_code=201, summary="Makine oluştur"
)
async def makine_olustur(
    govde: MakineOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    if await repository.makine_kod_var_mi(db, govde.kod):
        raise CakismaHatasi("Bu kod ile makine zaten var")
    makine = await repository.makine_ekle(
        db, Makine(kod=govde.kod, ad=govde.ad, oee_hedefi=govde.oee_hedefi)
    )
    await denetim_yaz(
        db, eylem="olustur", kaynak="makine", kaynak_id=str(makine.id), kullanici=kullanici
    )
    return basari(_makine_cevap(makine), mesaj="Makine oluşturuldu")


@router.get("/makineler", response_model=Zarf[list[MakineCevapDTO]], summary="Makineleri listele")
async def makine_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
    durum: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.makine_listele(db, sayfa=sayfa, adet=adet, durum=durum)
    return sayfali([_makine_cevap(m) for m in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/makineler/{makine_id}", response_model=Zarf[MakineCevapDTO], summary="Makine detayı")
async def makine_detay(
    makine_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    makine = await repository.makine_getir(db, makine_id)
    if makine is None:
        raise KaynakBulunamadi("Makine bulunamadı")
    return basari(_makine_cevap(makine), mesaj="Makine detayı")


@router.patch(
    "/makineler/{makine_id}/durum",
    response_model=Zarf[MakineCevapDTO],
    summary="Makine durumunu güncelle",
)
async def makine_durum_guncelle(
    makine_id: int,
    govde: MakineDurumDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    if govde.durum not in MAKINE_DURUMLARI:
        raise DogrulamaHatasi(
            "Geçersiz durum",
            detaylar=[
                {"alan": "durum", "mesaj": f"Geçerli: {', '.join(sorted(MAKINE_DURUMLARI))}"}
            ],
        )
    makine = await repository.makine_getir(db, makine_id)
    if makine is None:
        raise KaynakBulunamadi("Makine bulunamadı")
    makine.durum = govde.durum
    await denetim_yaz(
        db,
        eylem="durum_guncelle",
        kaynak="makine",
        kaynak_id=str(makine.id),
        kullanici=kullanici,
        detay={"durum": govde.durum},
    )
    return basari(_makine_cevap(makine), mesaj="Durum güncellendi")


@router.get("/makineler/{makine_id}/oee", response_model=Zarf[OeeCevapDTO], summary="Makine OEE")
async def makine_oee(
    makine_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    baslangic: Annotated[datetime | None, Query()] = None,
    bitis: Annotated[datetime | None, Query()] = None,
) -> dict[str, Any]:
    makine = await repository.makine_getir(db, makine_id)
    if makine is None:
        raise KaynakBulunamadi("Makine bulunamadı")
    sonuc, sayi = await service.makine_oee(db, makine_id, baslangic=baslangic, bitis=bitis)
    veri = OeeCevapDTO(
        makine_id=makine_id,
        kullanilabilirlik=sonuc.kullanilabilirlik,
        performans=sonuc.performans,
        kalite=sonuc.kalite,
        oee=sonuc.oee,
        kayit_sayisi=sayi,
    )
    return basari(veri.model_dump(), mesaj="OEE hesaplandı")


# --- Üretim verileri ---
@router.post(
    "/uretim-verileri",
    response_model=Zarf[UretimVerisiCevapDTO],
    status_code=201,
    summary="Üretim verisi girişi",
)
async def uretim_girisi(
    govde: UretimGirisDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    if govde.saglam_adet > govde.toplam_adet:
        raise DogrulamaHatasi(
            "Sağlam adet toplam adetten büyük olamaz",
            detaylar=[{"alan": "saglam_adet", "mesaj": "toplam_adet'i aşamaz"}],
        )
    if await repository.makine_getir(db, govde.makine_id) is None:
        raise KaynakBulunamadi("Makine bulunamadı")

    kayit = await repository.uretim_ekle(
        db,
        UretimVerisi(
            makine_id=govde.makine_id,
            zaman=govde.zaman or datetime.now(UTC),
            vardiya=govde.vardiya,
            planlanan_sure_dk=govde.planlanan_sure_dk,
            durus_sure_dk=govde.durus_sure_dk,
            toplam_adet=govde.toplam_adet,
            saglam_adet=govde.saglam_adet,
            ideal_cevrim_sn=govde.ideal_cevrim_sn,
        ),
    )
    await denetim_yaz(
        db, eylem="olustur", kaynak="uretim_verisi", kaynak_id=str(kayit.id), kullanici=kullanici
    )
    return basari(_uretim_cevap(kayit), mesaj="Üretim verisi kaydedildi")


@router.get(
    "/uretim-verileri",
    response_model=Zarf[list[UretimVerisiCevapDTO]],
    summary="Üretim verilerini listele",
)
async def uretim_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
    makine_id: int | None = None,
    baslangic: Annotated[datetime | None, Query()] = None,
    bitis: Annotated[datetime | None, Query()] = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.uretim_listele(
        db, sayfa=sayfa, adet=adet, makine_id=makine_id, baslangic=baslangic, bitis=bitis
    )
    return sayfali([_uretim_cevap(u) for u in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/oee/ozet", response_model=Zarf[list[OeeOzetSatirDTO]], summary="Makine bazlı OEE özeti"
)
async def oee_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    baslangic: Annotated[datetime | None, Query()] = None,
    bitis: Annotated[datetime | None, Query()] = None,
) -> dict[str, Any]:
    satirlar = await service.oee_ozet(db, baslangic=baslangic, bitis=bitis)
    veri = [
        OeeOzetSatirDTO(
            makine_id=mid,
            makine_kod=kod,
            kullanilabilirlik=s.kullanilabilirlik,
            performans=s.performans,
            kalite=s.kalite,
            oee=s.oee,
            kayit_sayisi=sayi,
        ).model_dump()
        for mid, kod, s, sayi in satirlar
    ]
    return basari(veri, mesaj="OEE özeti")
