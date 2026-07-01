"""Stok & Satınalma uçları (``/api/v1``).

Tüm uçlar tenant-kapsamlı + RBAC korumalı; yazma işlemleri audit'lenir. Hareket ve
satınalma uçları sonraki task'larda eklenir.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.stok import repository, service
from app.modules.stok.birimler import BIRIMLER, STOK_HAREKET_TURLERI
from app.modules.stok.models import Malzeme, StokHareketi
from app.modules.stok.schemas import (
    MalzemeCevapDTO,
    MalzemeGuncelleDTO,
    MalzemeOlusturDTO,
    StokHareketiCevapDTO,
    StokHareketiOlusturDTO,
)

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


# --- Stok hareketi ---
def _hareket_cevap(h: StokHareketi) -> dict[str, Any]:
    return StokHareketiCevapDTO(
        id=h.id,
        malzeme_id=h.malzeme_id,
        tur=h.tur,
        miktar=float(h.miktar),
        bakiye_sonrasi=float(h.bakiye_sonrasi),
        aciklama=h.aciklama,
        kaynak=h.kaynak,
        olusturan_kullanici_id=h.olusturan_kullanici_id,
        olusturma_tarihi=h.olusturma_tarihi,
    ).model_dump()


@router.post(
    "/stok-hareketleri",
    response_model=Zarf[StokHareketiCevapDTO],
    status_code=201,
    summary="Stok hareketi ekle (giriş/çıkış/düzeltme)",
)
async def stok_hareketi_olustur(
    govde: StokHareketiOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    if govde.tur not in STOK_HAREKET_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz hareket türü",
            detaylar=[
                {"alan": "tur", "mesaj": f"Geçerli: {', '.join(sorted(STOK_HAREKET_TURLERI))}"}
            ],
        )
    if idempotency_key is not None:
        mevcut = await repository.hareket_idempotent_getir(db, idempotency_key)
        if mevcut is not None:
            return basari(_hareket_cevap(mevcut), mesaj="Hareket zaten işlenmiş")

    malzeme = await repository.malzeme_getir_kilitli(db, govde.malzeme_id)
    if malzeme is None:
        raise KaynakBulunamadi("Malzeme bulunamadı")

    hareket, kritige_dustu = await service.stok_hareketi_uygula(
        db,
        malzeme,
        tur=govde.tur,
        miktar=govde.miktar,
        aciklama=govde.aciklama,
        kaynak=govde.kaynak,
        kullanici=kullanici,
        idempotency_anahtari=idempotency_key,
    )
    await denetim_yaz(
        db,
        eylem="hareket",
        kaynak="stok_hareketi",
        kaynak_id=str(hareket.id),
        kullanici=kullanici,
        detay={"tur": govde.tur, "malzeme_id": malzeme.id},
    )
    await yayinla(tenant.slug, {"tur": "stok.hareket", "malzeme_id": malzeme.id})
    if kritige_dustu:
        await yayinla(
            tenant.slug, {"tur": "stok.kritik", "malzeme_id": malzeme.id, "kod": malzeme.kod}
        )
    return basari(_hareket_cevap(hareket), mesaj="Stok hareketi eklendi")


@router.get(
    "/stok-hareketleri",
    response_model=Zarf[list[StokHareketiCevapDTO]],
    summary="Stok hareketlerini listele",
)
async def stok_hareketi_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("stok:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    malzeme_id: int | None = None,
    tur: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.hareket_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        malzeme_id=malzeme_id,
        tur=tur,
        baslangic=baslangic,
        bitis=bitis,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_hareket_cevap(x) for x in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)
