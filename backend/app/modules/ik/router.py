"""İK uçları (``/api/v1``) — personel + izin talebi + fazla mesai + zimmet + sertifika.

Tüm uçlar tenant-kapsamlı + RBAC. Personel/izin/mesai/zimmet/sertifika okuma ``ik:oku``,
yazma ``ik:yaz`` ister; izin talebi **onay/red** ayrıca ``ik:onay`` ister (görev ayrımı).
KVKK: personel yanıtlarında TC kimlik ``tc_maskele`` ile maskelenir.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.ik import repository, service
from app.modules.ik.models import Personel
from app.modules.ik.schemas import (
    PersonelCevapDTO,
    PersonelGuncelleDTO,
    PersonelOlusturDTO,
)

router = APIRouter(tags=["İK"])


# --- Personel (KVKK: TC maskeli) ---
def _personel_cevap(p: Personel) -> dict[str, Any]:
    return PersonelCevapDTO(
        id=p.id,
        sicil_no=p.sicil_no,
        ad=p.ad,
        soyad=p.soyad,
        tc_kimlik_no=service.tc_maskele(p.tc_kimlik_no),
        dogum_tarihi=p.dogum_tarihi,
        telefon=p.telefon,
        eposta=p.eposta,
        departman=p.departman,
        unvan=p.unvan,
        ise_giris_tarihi=p.ise_giris_tarihi,
        yillik_izin_hakki=p.yillik_izin_hakki,
        kullanici_id=p.kullanici_id,
        aktif=p.aktif,
        olusturma_tarihi=p.olusturma_tarihi,
    ).model_dump()


@router.post(
    "/personeller",
    response_model=Zarf[PersonelCevapDTO],
    status_code=201,
    summary="Personel oluştur",
)
async def personel_olustur(
    govde: PersonelOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if await repository.personel_sicil_ile(db, govde.sicil_no) is not None:
        raise CakismaHatasi(f"Sicil no zaten kayıtlı: {govde.sicil_no}")
    personel = Personel(
        sicil_no=govde.sicil_no,
        ad=govde.ad,
        soyad=govde.soyad,
        tc_kimlik_no=govde.tc_kimlik_no,
        dogum_tarihi=govde.dogum_tarihi,
        telefon=govde.telefon,
        eposta=govde.eposta,
        departman=govde.departman,
        unvan=govde.unvan,
        ise_giris_tarihi=govde.ise_giris_tarihi,
        yillik_izin_hakki=govde.yillik_izin_hakki,
        kullanici_id=govde.kullanici_id,
        aktif=govde.aktif,
    )
    await repository.personel_ekle(db, personel)
    await denetim_yaz(
        db, eylem="olustur", kaynak="personel", kaynak_id=str(personel.id), kullanici=kullanici
    )
    return basari(_personel_cevap(personel), mesaj="Personel oluşturuldu")


@router.get(
    "/personeller",
    response_model=Zarf[list[PersonelCevapDTO]],
    summary="Personelleri listele",
)
async def personel_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    departman: str | None = None,
    aktif: bool | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.personel_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        departman=departman,
        aktif=aktif,
        arama=arama,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_personel_cevap(p) for p in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/personeller/{personel_id}",
    response_model=Zarf[PersonelCevapDTO],
    summary="Personel detayı",
)
async def personel_detay(
    personel_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    personel = await repository.personel_getir(db, personel_id)
    if personel is None:
        raise KaynakBulunamadi("Personel bulunamadı")
    return basari(_personel_cevap(personel), mesaj="Personel detayı")


@router.patch(
    "/personeller/{personel_id}",
    response_model=Zarf[PersonelCevapDTO],
    summary="Personel düzenle",
)
async def personel_guncelle(
    personel_id: int,
    govde: PersonelGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    personel = await repository.personel_getir(db, personel_id)
    if personel is None:
        raise KaynakBulunamadi("Personel bulunamadı")
    for alan in (
        "ad",
        "soyad",
        "tc_kimlik_no",
        "dogum_tarihi",
        "telefon",
        "eposta",
        "departman",
        "unvan",
        "ise_giris_tarihi",
        "yillik_izin_hakki",
        "kullanici_id",
        "aktif",
    ):
        deger = getattr(govde, alan)
        if deger is not None:
            setattr(personel, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="personel", kaynak_id=str(personel.id), kullanici=kullanici
    )
    return basari(_personel_cevap(personel), mesaj="Personel güncellendi")
