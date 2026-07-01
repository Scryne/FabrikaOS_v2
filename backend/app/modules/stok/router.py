"""Stok & Satınalma uçları (``/api/v1``).

Tüm uçlar tenant-kapsamlı + RBAC korumalı; yazma işlemleri audit'lenir. Hareket ve
satınalma uçları sonraki task'larda eklenir.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.stok import repository
from app.modules.stok.birimler import BIRIMLER
from app.modules.stok.models import Malzeme
from app.modules.stok.schemas import MalzemeCevapDTO, MalzemeGuncelleDTO, MalzemeOlusturDTO

router = APIRouter(tags=["Stok & Satınalma"])


def _malzeme_cevap(m: Malzeme) -> dict[str, Any]:
    kritik = m.kritik_stok > 0 and m.mevcut_miktar <= m.kritik_stok
    return MalzemeCevapDTO(
        id=m.id,
        kod=m.kod,
        ad=m.ad,
        birim=m.birim,
        kategori=m.kategori,
        mevcut_miktar=float(m.mevcut_miktar),
        min_stok=float(m.min_stok),
        max_stok=float(m.max_stok) if m.max_stok is not None else None,
        kritik_stok=float(m.kritik_stok),
        aktif=m.aktif,
        kritik=kritik,
        olusturma_tarihi=m.olusturma_tarihi,
    ).model_dump()


def _birim_dogrula(birim: str) -> None:
    if birim not in BIRIMLER:
        raise DogrulamaHatasi(
            "Geçersiz birim",
            detaylar=[{"alan": "birim", "mesaj": f"Geçerli: {', '.join(sorted(BIRIMLER))}"}],
        )


@router.post(
    "/malzemeler", response_model=Zarf[MalzemeCevapDTO], status_code=201, summary="Malzeme oluştur"
)
async def malzeme_olustur(
    govde: MalzemeOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _birim_dogrula(govde.birim)
    if await repository.malzeme_kod_var_mi(db, govde.kod):
        raise CakismaHatasi("Bu kod ile malzeme zaten var")
    malzeme = Malzeme(
        kod=govde.kod,
        ad=govde.ad,
        birim=govde.birim,
        kategori=govde.kategori,
        min_stok=govde.min_stok,
        max_stok=govde.max_stok,
        kritik_stok=govde.kritik_stok,
    )
    await repository.malzeme_ekle(db, malzeme)
    await denetim_yaz(
        db, eylem="olustur", kaynak="malzeme", kaynak_id=str(malzeme.id), kullanici=kullanici
    )
    return basari(_malzeme_cevap(malzeme), mesaj="Malzeme oluşturuldu")


@router.get(
    "/malzemeler", response_model=Zarf[list[MalzemeCevapDTO]], summary="Malzemeleri listele"
)
async def malzeme_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    arama: str | None = None,
    kategori: str | None = None,
    aktif: bool | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.malzeme_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        arama=arama,
        kategori=kategori,
        aktif=aktif,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_malzeme_cevap(m) for m in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/stok/kritik", response_model=Zarf[list[MalzemeCevapDTO]], summary="Kritik stoktakiler"
)
async def kritik_stok(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kayitlar = await repository.kritik_listele(db)
    return basari([_malzeme_cevap(m) for m in kayitlar], mesaj="Kritik stok")


@router.get(
    "/malzemeler/{malzeme_id}", response_model=Zarf[MalzemeCevapDTO], summary="Malzeme detayı"
)
async def malzeme_detay(
    malzeme_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    malzeme = await repository.malzeme_getir(db, malzeme_id)
    if malzeme is None:
        raise KaynakBulunamadi("Malzeme bulunamadı")
    return basari(_malzeme_cevap(malzeme), mesaj="Malzeme detayı")


@router.patch(
    "/malzemeler/{malzeme_id}", response_model=Zarf[MalzemeCevapDTO], summary="Malzeme güncelle"
)
async def malzeme_guncelle(
    malzeme_id: int,
    govde: MalzemeGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    malzeme = await repository.malzeme_getir(db, malzeme_id)
    if malzeme is None:
        raise KaynakBulunamadi("Malzeme bulunamadı")
    if govde.birim is not None:
        _birim_dogrula(govde.birim)
        malzeme.birim = govde.birim
    for alan in ("ad", "kategori", "min_stok", "max_stok", "kritik_stok", "aktif"):
        deger = getattr(govde, alan)
        if deger is not None:
            setattr(malzeme, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="malzeme", kaynak_id=str(malzeme.id), kullanici=kullanici
    )
    return basari(_malzeme_cevap(malzeme), mesaj="Malzeme güncellendi")
