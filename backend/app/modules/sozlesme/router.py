"""Sözleşme uçları (``/api/v1``) — CRUD + durum geçiş + yaklaşan bitiş taraması.

Tüm uçlar tenant-kapsamlı + RBAC. Okuma ``sozlesme:oku``, yazma/durum/tara ``sozlesme:yaz``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.crm import repository as crm_repo
from app.modules.sozlesme import repository, service
from app.modules.sozlesme.birimler import SOZLESME_TURLERI
from app.modules.sozlesme.models import Sozlesme
from app.modules.sozlesme.schemas import (
    SozlesmeCevapDTO,
    SozlesmeDurumDTO,
    SozlesmeGuncelleDTO,
    SozlesmeOlusturDTO,
    SozlesmeOzetDTO,
    SozlesmeSayiDTO,
    YaklasanTaraDTO,
)

router = APIRouter(tags=["Sözleşme"], dependencies=[Depends(modul_gerekli("sozlesme"))])


def _cevap(s: Sozlesme) -> dict[str, Any]:
    return SozlesmeCevapDTO(
        id=s.id,
        kod=s.kod,
        firma_id=s.firma_id,
        baslik=s.baslik,
        tur=s.tur,
        baslangic_tarihi=s.baslangic_tarihi,
        bitis_tarihi=s.bitis_tarihi,
        tutar=float(s.tutar),
        para_birimi=s.para_birimi,
        durum=s.durum,
        sorumlu_kullanici_id=s.sorumlu_kullanici_id,
        yaklasim_bildirildi=s.yaklasim_bildirildi,
        aciklama=s.aciklama,
        olusturma_tarihi=s.olusturma_tarihi,
    ).model_dump()


def _tur_dogrula(tur: str) -> None:
    if tur not in SOZLESME_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz sözleşme türü",
            detaylar=[{"alan": "tur", "mesaj": f"Geçerli: {', '.join(sorted(SOZLESME_TURLERI))}"}],
        )


@router.post(
    "/sozlesmeler",
    response_model=Zarf[SozlesmeCevapDTO],
    status_code=201,
    summary="Sözleşme oluştur",
)
async def sozlesme_olustur(
    govde: SozlesmeOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("sozlesme:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _tur_dogrula(govde.tur)
    if govde.bitis_tarihi < govde.baslangic_tarihi:
        raise DogrulamaHatasi(
            "Bitiş tarihi başlangıçtan önce olamaz",
            detaylar=[{"alan": "bitis_tarihi", "mesaj": ">= baslangic_tarihi"}],
        )
    if await crm_repo.firma_getir(db, govde.firma_id) is None:
        raise KaynakBulunamadi("Firma bulunamadı")
    sozlesme = Sozlesme(kod=service.sozlesme_gecici_kod(), **govde.model_dump())
    await repository.ekle(db, sozlesme)
    sozlesme.kod = service.sozlesme_kalici_kod(sozlesme.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="sozlesme", kaynak_id=str(sozlesme.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "sozlesme.durum", "id": sozlesme.id})
    return basari(_cevap(sozlesme), mesaj="Sözleşme oluşturuldu")


@router.get(
    "/sozlesmeler", response_model=Zarf[list[SozlesmeCevapDTO]], summary="Sözleşmeleri listele"
)
async def sozlesme_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("sozlesme:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    firma_id: int | None = None,
    durum: str | None = None,
    tur: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.listele(
        db,
        sayfa=sayfa,
        adet=adet,
        firma_id=firma_id,
        durum=durum,
        tur=tur,
        arama=arama,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_cevap(s) for s in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/sozlesmeler/yaklasan",
    response_model=Zarf[list[SozlesmeCevapDTO]],
    summary="Yaklaşan bitişli sözleşmeler",
)
async def sozlesme_yaklasan(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("sozlesme:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    esik_gun: int = 30,
) -> dict[str, Any]:
    esik_gun = min(max(esik_gun, 1), 365)
    bugun = datetime.now(UTC).date()
    sinir = bugun + timedelta(days=esik_gun)
    kayitlar = await repository.yaklasan_listele(db, bugun=bugun, sinir=sinir)
    return basari([_cevap(s) for s in kayitlar], mesaj="Yaklaşan sözleşmeler")


@router.post(
    "/sozlesmeler/yaklasanlari-tara",
    response_model=Zarf[dict[str, int]],
    summary="Yaklaşan sözleşmeleri tara (sozlesme.yaklasiyor olayı üret)",
)
async def sozlesme_yaklasan_tara(
    govde: YaklasanTaraDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("sozlesme:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    adet = await service.yaklasan_tara(db, tenant_slug=tenant.slug, esik_gun=govde.esik_gun)
    await denetim_yaz(
        db, eylem="tara", kaynak="sozlesme", kaynak_id="yaklasan", kullanici=kullanici
    )
    return basari({"islenen": adet}, mesaj="Tarama tamamlandı")


@router.get(
    "/sozlesmeler/{sozlesme_id}", response_model=Zarf[SozlesmeCevapDTO], summary="Sözleşme detayı"
)
async def sozlesme_detay(
    sozlesme_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("sozlesme:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    sozlesme = await repository.getir(db, sozlesme_id)
    if sozlesme is None:
        raise KaynakBulunamadi("Sözleşme bulunamadı")
    return basari(_cevap(sozlesme), mesaj="Sözleşme detayı")


@router.patch(
    "/sozlesmeler/{sozlesme_id}", response_model=Zarf[SozlesmeCevapDTO], summary="Sözleşme düzenle"
)
async def sozlesme_guncelle(
    sozlesme_id: int,
    govde: SozlesmeGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("sozlesme:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    sozlesme = await repository.getir(db, sozlesme_id)
    if sozlesme is None:
        raise KaynakBulunamadi("Sözleşme bulunamadı")
    if govde.tur is not None:
        _tur_dogrula(govde.tur)
    for alan, deger in govde.model_dump(exclude_unset=True).items():
        if deger is not None:
            setattr(sozlesme, alan, deger)
    if sozlesme.bitis_tarihi < sozlesme.baslangic_tarihi:
        raise DogrulamaHatasi(
            "Bitiş tarihi başlangıçtan önce olamaz",
            detaylar=[{"alan": "bitis_tarihi", "mesaj": ">= baslangic_tarihi"}],
        )
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="sozlesme", kaynak_id=str(sozlesme.id), kullanici=kullanici
    )
    return basari(_cevap(sozlesme), mesaj="Sözleşme güncellendi")


@router.patch(
    "/sozlesmeler/{sozlesme_id}/durum",
    response_model=Zarf[SozlesmeCevapDTO],
    summary="Sözleşme durumunu değiştir",
)
async def sozlesme_durum(
    sozlesme_id: int,
    govde: SozlesmeDurumDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("sozlesme:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    sozlesme = await repository.getir_kilitli(db, sozlesme_id)
    if sozlesme is None:
        raise KaynakBulunamadi("Sözleşme bulunamadı")
    await service.sozlesme_durum_gecisi(db, sozlesme, hedef=govde.durum)
    await denetim_yaz(
        db,
        eylem="durum_guncelle",
        kaynak="sozlesme",
        kaynak_id=str(sozlesme.id),
        kullanici=kullanici,
        detay={"durum": sozlesme.durum},
    )
    await yayinla(tenant.slug, {"tur": "sozlesme.durum", "id": sozlesme.id})
    return basari(_cevap(sozlesme), mesaj="Durum güncellendi")


@router.get("/sozlesme/ozet", response_model=Zarf[SozlesmeOzetDTO], summary="Sözleşme özeti (KPI)")
async def sozlesme_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("sozlesme:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    durum_sonuc = await db.execute(select(Sozlesme.durum, func.count()).group_by(Sozlesme.durum))
    sayac: dict[str, int] = {}
    for d, adet in durum_sonuc.all():
        sayac[d] = int(adet)

    bugun = datetime.now(UTC).date()
    sinir = bugun + timedelta(days=30)
    yaklasan = (
        await db.scalar(
            select(func.count())
            .select_from(Sozlesme)
            .where(
                Sozlesme.durum == "aktif",
                Sozlesme.bitis_tarihi >= bugun,
                Sozlesme.bitis_tarihi <= sinir,
            )
        )
        or 0
    )

    ozet = SozlesmeOzetDTO(
        aktif=sayac.get("aktif", 0),
        yaklasan=int(yaklasan),
        taslak=sayac.get("taslak", 0),
        toplam=sum(sayac.values()),
        durum_dagilimi=[SozlesmeSayiDTO(durum=d, adet=a) for d, a in sorted(sayac.items())],
    )
    return basari(ozet.model_dump(), mesaj="Sözleşme özeti")
