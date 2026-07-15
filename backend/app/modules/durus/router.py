"""Duruş uçları (``/api/v1``) — neden kataloğu + kayıt + pareto analizi.

Okuma ``uretim:oku``, yazma ``uretim:yaz``; modül kapısı ``uretim``. Kayıtlı duruş
dakikaları OEE kullanılabilirlik hesabına girer (``uretim.service``); pareto ucu
neden bazında 80/20 kırılımı döner.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.durus import repository
from app.modules.durus.models import DURUS_SINIFLARI, DurusKaydi, DurusNedeni
from app.modules.durus.pareto import pareto_hesapla
from app.modules.uretim import repository as uretim_repository

router = APIRouter(tags=["Duruş"], dependencies=[Depends(modul_gerekli("uretim"))])


class DurusNedeniOlusturDTO(BaseModel):
    ad: str = Field(min_length=1, max_length=100)
    sinif: str = Field(default="plansiz", max_length=10)


class DurusNedeniGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=100)
    sinif: str | None = Field(default=None, max_length=10)
    aktif: bool | None = None


class DurusNedeniCevapDTO(BaseModel):
    id: int
    ad: str
    sinif: str
    aktif: bool


class DurusKaydiOlusturDTO(BaseModel):
    makine_id: int
    neden_id: int
    baslangic: datetime
    bitis: datetime
    aciklama: str = Field(default="", max_length=500)


class DurusKaydiCevapDTO(BaseModel):
    id: int
    makine_id: int
    neden_id: int
    baslangic: datetime
    bitis: datetime
    sure_dk: float
    aciklama: str
    olusturma_tarihi: datetime


class ParetoSatirDTO(BaseModel):
    neden: str
    sinif: str
    toplam_dk: float
    yuzde: float
    kumulatif_yuzde: float


def _neden_cevap(n: DurusNedeni) -> dict[str, Any]:
    return DurusNedeniCevapDTO(id=n.id, ad=n.ad, sinif=n.sinif, aktif=n.aktif).model_dump()


def _kayit_cevap(k: DurusKaydi) -> dict[str, Any]:
    return DurusKaydiCevapDTO(
        id=k.id,
        makine_id=k.makine_id,
        neden_id=k.neden_id,
        baslangic=k.baslangic,
        bitis=k.bitis,
        sure_dk=round(k.sure_dk, 1),
        aciklama=k.aciklama,
        olusturma_tarihi=k.olusturma_tarihi,
    ).model_dump()


def _sinif_dogrula(sinif: str) -> None:
    if sinif not in DURUS_SINIFLARI:
        raise DogrulamaHatasi(
            "Geçersiz duruş sınıfı",
            detaylar=[{"alan": "sinif", "mesaj": f"Geçerli: {', '.join(sorted(DURUS_SINIFLARI))}"}],
        )


# --- Neden kataloğu ---
@router.get(
    "/durus-nedenleri",
    response_model=Zarf[list[DurusNedeniCevapDTO]],
    summary="Duruş nedeni kataloğu",
)
async def neden_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kayitlar = (await db.execute(select(DurusNedeni).order_by(DurusNedeni.ad))).scalars().all()
    return basari([_neden_cevap(n) for n in kayitlar], mesaj="Duruş nedenleri")


@router.post(
    "/durus-nedenleri",
    response_model=Zarf[DurusNedeniCevapDTO],
    status_code=201,
    summary="Duruş nedeni oluştur",
)
async def neden_olustur(
    govde: DurusNedeniOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _sinif_dogrula(govde.sinif)
    mevcut = (
        await db.execute(select(DurusNedeni.id).where(DurusNedeni.ad == govde.ad))
    ).scalar_one_or_none()
    if mevcut is not None:
        raise CakismaHatasi("Bu ad ile duruş nedeni zaten var")
    neden = DurusNedeni(ad=govde.ad, sinif=govde.sinif)
    db.add(neden)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="durus_nedeni", kaynak_id=str(neden.id), kullanici=kullanici
    )
    return basari(_neden_cevap(neden), mesaj="Duruş nedeni oluşturuldu")


@router.patch(
    "/durus-nedenleri/{neden_id}",
    response_model=Zarf[DurusNedeniCevapDTO],
    summary="Duruş nedeni düzenle",
)
async def neden_guncelle(
    neden_id: int,
    govde: DurusNedeniGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    neden = await db.get(DurusNedeni, neden_id)
    if neden is None:
        raise KaynakBulunamadi("Duruş nedeni bulunamadı")
    if govde.sinif is not None:
        _sinif_dogrula(govde.sinif)
    for alan, deger in govde.model_dump(exclude_unset=True).items():
        if deger is not None:
            setattr(neden, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="durus_nedeni", kaynak_id=str(neden.id), kullanici=kullanici
    )
    return basari(_neden_cevap(neden), mesaj="Duruş nedeni güncellendi")


# --- Kayıtlar ---
@router.get(
    "/durus-kayitlari",
    response_model=Zarf[list[DurusKaydiCevapDTO]],
    summary="Duruş kayıtları (sayfalı)",
)
async def kayit_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    makine_id: int | None = None,
    neden_id: int | None = None,
    baslangic: Annotated[datetime | None, Query()] = None,
    bitis: Annotated[datetime | None, Query()] = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.kayit_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        makine_id=makine_id,
        neden_id=neden_id,
        baslangic=baslangic,
        bitis=bitis,
    )
    return sayfali([_kayit_cevap(k) for k in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.post(
    "/durus-kayitlari",
    response_model=Zarf[DurusKaydiCevapDTO],
    status_code=201,
    summary="Duruş kaydı oluştur",
)
async def kayit_olustur(
    govde: DurusKaydiOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if govde.bitis <= govde.baslangic:
        raise DogrulamaHatasi(
            "Bitiş başlangıçtan sonra olmalı",
            detaylar=[{"alan": "bitis", "mesaj": "> baslangic"}],
        )
    if await uretim_repository.makine_getir(db, govde.makine_id) is None:
        raise KaynakBulunamadi("Makine bulunamadı")
    neden = await db.get(DurusNedeni, govde.neden_id)
    if neden is None:
        raise KaynakBulunamadi("Duruş nedeni bulunamadı")
    kayit = DurusKaydi(
        makine_id=govde.makine_id,
        neden_id=govde.neden_id,
        baslangic=govde.baslangic,
        bitis=govde.bitis,
        aciklama=govde.aciklama,
        olusturan_kullanici_id=kullanici.id,
    )
    db.add(kayit)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="durus_kaydi", kaynak_id=str(kayit.id), kullanici=kullanici
    )
    return basari(_kayit_cevap(kayit), mesaj="Duruş kaydı oluşturuldu")


@router.get(
    "/durus/pareto",
    response_model=Zarf[list[ParetoSatirDTO]],
    summary="Duruş pareto analizi (neden bazında 80/20)",
)
async def durus_pareto(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    gun: Annotated[int, Query(ge=1, le=365)] = 30,
) -> dict[str, Any]:
    simdi = datetime.now(UTC)
    girdiler = await repository.pareto_girdileri(
        db, baslangic=simdi - timedelta(days=gun), bitis=simdi
    )
    satirlar = pareto_hesapla(girdiler)
    return basari(
        [
            ParetoSatirDTO(
                neden=s.neden,
                sinif=s.sinif,
                toplam_dk=s.toplam_dk,
                yuzde=s.yuzde,
                kumulatif_yuzde=s.kumulatif_yuzde,
            ).model_dump()
            for s in satirlar
        ],
        mesaj="Duruş pareto",
    )
