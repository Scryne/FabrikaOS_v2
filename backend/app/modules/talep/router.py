"""Talep uçları (``/api/v1``) — CRUD + durum geçiş + atama.

Tüm uçlar tenant-kapsamlı + RBAC. Okuma ``talep:oku``, yazma/durum ``talep:yaz``.
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
from app.modules.crm import repository as crm_repo
from app.modules.talep import repository, service
from app.modules.talep.birimler import ONCELIKLER, TALEP_TURLERI
from app.modules.talep.models import Talep
from app.modules.talep.schemas import (
    TalepCevapDTO,
    TalepDurumDTO,
    TalepGuncelleDTO,
    TalepOlusturDTO,
)

router = APIRouter(tags=["Talep"])


def _cevap(t: Talep) -> dict[str, Any]:
    return TalepCevapDTO(
        id=t.id,
        kod=t.kod,
        firma_id=t.firma_id,
        baslik=t.baslik,
        aciklama=t.aciklama,
        tur=t.tur,
        oncelik=t.oncelik,
        durum=t.durum,
        atanan_kullanici_id=t.atanan_kullanici_id,
        talep_eden_kullanici_id=t.talep_eden_kullanici_id,
        talep_eden_ad=t.talep_eden_ad,
        olusturma_tarihi=t.olusturma_tarihi,
    ).model_dump()


def _tur_dogrula(tur: str) -> None:
    if tur not in TALEP_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz talep türü",
            detaylar=[{"alan": "tur", "mesaj": f"Geçerli: {', '.join(sorted(TALEP_TURLERI))}"}],
        )


def _oncelik_dogrula(oncelik: str) -> None:
    if oncelik not in ONCELIKLER:
        raise DogrulamaHatasi(
            "Geçersiz öncelik",
            detaylar=[{"alan": "oncelik", "mesaj": f"Geçerli: {', '.join(sorted(ONCELIKLER))}"}],
        )


async def _firma_kontrol(db: AsyncSession, firma_id: int | None) -> None:
    if firma_id is not None and await crm_repo.firma_getir(db, firma_id) is None:
        raise KaynakBulunamadi("Firma bulunamadı")


@router.post(
    "/talepler", response_model=Zarf[TalepCevapDTO], status_code=201, summary="Talep oluştur"
)
async def talep_olustur(
    govde: TalepOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("talep:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _tur_dogrula(govde.tur)
    _oncelik_dogrula(govde.oncelik)
    await _firma_kontrol(db, govde.firma_id)
    talep = Talep(
        kod=service.talep_gecici_kod(),
        talep_eden_kullanici_id=kullanici.id,
        **govde.model_dump(),
    )
    await repository.ekle(db, talep)
    talep.kod = service.talep_kalici_kod(talep.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="talep", kaynak_id=str(talep.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "talep.olusturuldu", "id": talep.id})
    return basari(_cevap(talep), mesaj="Talep oluşturuldu")


@router.get("/talepler", response_model=Zarf[list[TalepCevapDTO]], summary="Talepleri listele")
async def talep_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("talep:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    firma_id: int | None = None,
    durum: str | None = None,
    oncelik: str | None = None,
    tur: str | None = None,
    atanan_kullanici_id: int | None = None,
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
        oncelik=oncelik,
        tur=tur,
        atanan_kullanici_id=atanan_kullanici_id,
        arama=arama,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_cevap(t) for t in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/talepler/{talep_id}", response_model=Zarf[TalepCevapDTO], summary="Talep detayı")
async def talep_detay(
    talep_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("talep:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    talep = await repository.getir(db, talep_id)
    if talep is None:
        raise KaynakBulunamadi("Talep bulunamadı")
    return basari(_cevap(talep), mesaj="Talep detayı")


@router.patch("/talepler/{talep_id}", response_model=Zarf[TalepCevapDTO], summary="Talep düzenle")
async def talep_guncelle(
    talep_id: int,
    govde: TalepGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("talep:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    talep = await repository.getir(db, talep_id)
    if talep is None:
        raise KaynakBulunamadi("Talep bulunamadı")
    guncel = govde.model_dump(exclude_unset=True)
    if govde.tur is not None:
        _tur_dogrula(govde.tur)
    if govde.oncelik is not None:
        _oncelik_dogrula(govde.oncelik)
    if "firma_id" in guncel:
        await _firma_kontrol(db, govde.firma_id)
    for alan, deger in guncel.items():
        if deger is not None:
            setattr(talep, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="talep", kaynak_id=str(talep.id), kullanici=kullanici
    )
    return basari(_cevap(talep), mesaj="Talep güncellendi")


@router.patch(
    "/talepler/{talep_id}/durum",
    response_model=Zarf[TalepCevapDTO],
    summary="Talep durumunu değiştir",
)
async def talep_durum(
    talep_id: int,
    govde: TalepDurumDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("talep:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    talep = await repository.getir_kilitli(db, talep_id)
    if talep is None:
        raise KaynakBulunamadi("Talep bulunamadı")
    await service.talep_durum_gecisi(db, talep, hedef=govde.durum)
    await denetim_yaz(
        db,
        eylem="durum_guncelle",
        kaynak="talep",
        kaynak_id=str(talep.id),
        kullanici=kullanici,
        detay={"durum": talep.durum},
    )
    await yayinla(tenant.slug, {"tur": "talep.durum", "id": talep.id})
    return basari(_cevap(talep), mesaj="Durum güncellendi")
