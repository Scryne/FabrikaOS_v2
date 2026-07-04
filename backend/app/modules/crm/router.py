"""CRM uçları (``/api/v1``) — firma + ortak (ilgili kişi).

Tüm uçlar tenant-kapsamlı + RBAC. Okuma ``crm:oku``, yazma ``crm:yaz``.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.crm import repository
from app.modules.crm.birimler import FIRMA_TIPLERI
from app.modules.crm.models import Firma, Ortak
from app.modules.crm.schemas import (
    FirmaCevapDTO,
    FirmaGuncelleDTO,
    FirmaOlusturDTO,
    OrtakCevapDTO,
    OrtakGuncelleDTO,
    OrtakOlusturDTO,
)

router = APIRouter(tags=["CRM"])


def _firma_cevap(f: Firma) -> dict[str, Any]:
    return FirmaCevapDTO(
        id=f.id,
        ad=f.ad,
        tip=f.tip,
        vergi_no=f.vergi_no,
        vergi_dairesi=f.vergi_dairesi,
        telefon=f.telefon,
        eposta=f.eposta,
        adres=f.adres,
        il=f.il,
        sektor=f.sektor,
        web_sitesi=f.web_sitesi,
        sorumlu_kullanici_id=f.sorumlu_kullanici_id,
        aktif=f.aktif,
        aciklama=f.aciklama,
        olusturma_tarihi=f.olusturma_tarihi,
    ).model_dump()


def _tip_dogrula(tip: str) -> None:
    if tip not in FIRMA_TIPLERI:
        raise DogrulamaHatasi(
            "Geçersiz firma tipi",
            detaylar=[{"alan": "tip", "mesaj": f"Geçerli: {', '.join(sorted(FIRMA_TIPLERI))}"}],
        )


@router.post(
    "/firmalar", response_model=Zarf[FirmaCevapDTO], status_code=201, summary="Firma oluştur"
)
async def firma_olustur(
    govde: FirmaOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("crm:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _tip_dogrula(govde.tip)
    firma = Firma(**govde.model_dump())
    await repository.firma_ekle(db, firma)
    await denetim_yaz(
        db, eylem="olustur", kaynak="firma", kaynak_id=str(firma.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "crm.firma", "id": firma.id})
    return basari(_firma_cevap(firma), mesaj="Firma oluşturuldu")


@router.get("/firmalar", response_model=Zarf[list[FirmaCevapDTO]], summary="Firmaları listele")
async def firma_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("crm:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    tip: str | None = None,
    aktif: bool | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.firma_listele(
        db, sayfa=sayfa, adet=adet, tip=tip, aktif=aktif, arama=arama, siralama=siralama, yon=yon
    )
    return sayfali([_firma_cevap(f) for f in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/firmalar/{firma_id}", response_model=Zarf[FirmaCevapDTO], summary="Firma detayı")
async def firma_detay(
    firma_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("crm:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    firma = await repository.firma_getir(db, firma_id)
    if firma is None:
        raise KaynakBulunamadi("Firma bulunamadı")
    return basari(_firma_cevap(firma), mesaj="Firma detayı")


@router.patch("/firmalar/{firma_id}", response_model=Zarf[FirmaCevapDTO], summary="Firma düzenle")
async def firma_guncelle(
    firma_id: int,
    govde: FirmaGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("crm:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    firma = await repository.firma_getir(db, firma_id)
    if firma is None:
        raise KaynakBulunamadi("Firma bulunamadı")
    if govde.tip is not None:
        _tip_dogrula(govde.tip)
    for alan, deger in govde.model_dump(exclude_unset=True).items():
        if deger is not None:
            setattr(firma, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="firma", kaynak_id=str(firma.id), kullanici=kullanici
    )
    return basari(_firma_cevap(firma), mesaj="Firma güncellendi")


# --- Ortak (firma ilgili kişisi) ---
def _ortak_cevap(o: Ortak) -> dict[str, Any]:
    return OrtakCevapDTO(
        id=o.id,
        firma_id=o.firma_id,
        ad_soyad=o.ad_soyad,
        unvan=o.unvan,
        telefon=o.telefon,
        eposta=o.eposta,
        birincil=o.birincil,
        aktif=o.aktif,
        aciklama=o.aciklama,
        olusturma_tarihi=o.olusturma_tarihi,
    ).model_dump()


@router.post(
    "/ortaklar", response_model=Zarf[OrtakCevapDTO], status_code=201, summary="Ortak (kontak) ekle"
)
async def ortak_olustur(
    govde: OrtakOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("crm:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if await repository.firma_getir(db, govde.firma_id) is None:
        raise KaynakBulunamadi("Firma bulunamadı")
    ortak = Ortak(**govde.model_dump())
    await repository.ortak_ekle(db, ortak)
    await denetim_yaz(
        db, eylem="olustur", kaynak="ortak", kaynak_id=str(ortak.id), kullanici=kullanici
    )
    return basari(_ortak_cevap(ortak), mesaj="Ortak eklendi")


@router.get("/ortaklar", response_model=Zarf[list[OrtakCevapDTO]], summary="Ortakları listele")
async def ortak_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("crm:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    firma_id: int | None = None,
    aktif: bool | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.ortak_listele(
        db, sayfa=sayfa, adet=adet, firma_id=firma_id, aktif=aktif
    )
    return sayfali([_ortak_cevap(o) for o in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.patch("/ortaklar/{ortak_id}", response_model=Zarf[OrtakCevapDTO], summary="Ortak düzenle")
async def ortak_guncelle(
    ortak_id: int,
    govde: OrtakGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("crm:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    ortak = await repository.ortak_getir(db, ortak_id)
    if ortak is None:
        raise KaynakBulunamadi("Ortak bulunamadı")
    for alan, deger in govde.model_dump(exclude_unset=True).items():
        if deger is not None:
            setattr(ortak, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="ortak", kaynak_id=str(ortak.id), kullanici=kullanici
    )
    return basari(_ortak_cevap(ortak), mesaj="Ortak güncellendi")
