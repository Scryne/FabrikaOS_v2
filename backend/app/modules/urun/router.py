"""Ürün & Reçete uçları (``/api/v1``).

Ürün CRUD + ürün başına reçete GET/PUT (**replace-all** — ikiz yerleşim deseni).
Okuma ``uretim:oku``, yazma ``uretim:yaz``; modül kapısı ``uretim``.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.stok.models import Malzeme
from app.modules.urun.models import Recete, ReceteKalemi, Urun

router = APIRouter(tags=["Ürün & Reçete"], dependencies=[Depends(modul_gerekli("uretim"))])


class UrunOlusturDTO(BaseModel):
    kod: str = Field(min_length=1, max_length=50)
    ad: str = Field(min_length=1, max_length=200)
    birim: str = Field(default="adet", max_length=20)
    aciklama: str = Field(default="", max_length=1000)


class UrunGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=200)
    birim: str | None = Field(default=None, max_length=20)
    aciklama: str | None = Field(default=None, max_length=1000)
    aktif: bool | None = None


class UrunCevapDTO(BaseModel):
    id: int
    kod: str
    ad: str
    birim: str
    aciklama: str
    aktif: bool
    olusturma_tarihi: datetime


class ReceteKalemGirisDTO(BaseModel):
    malzeme_id: int
    miktar: Decimal = Field(gt=0)


class ReceteKaydetDTO(BaseModel):
    ad: str = Field(default="", max_length=200)
    kalemler: list[ReceteKalemGirisDTO]


class ReceteKalemCevapDTO(BaseModel):
    malzeme_id: int
    malzeme_kod: str
    malzeme_ad: str
    birim: str
    miktar: float


class ReceteCevapDTO(BaseModel):
    urun_id: int
    ad: str
    aktif: bool
    kalemler: list[ReceteKalemCevapDTO]


def _urun_cevap(u: Urun) -> dict[str, Any]:
    return UrunCevapDTO(
        id=u.id,
        kod=u.kod,
        ad=u.ad,
        birim=u.birim,
        aciklama=u.aciklama,
        aktif=u.aktif,
        olusturma_tarihi=u.olusturma_tarihi,
    ).model_dump()


async def _recete_cevap(db: AsyncSession, recete: Recete) -> dict[str, Any]:
    malzeme_idler = [k.malzeme_id for k in recete.kalemler]
    malzemeler = {
        m.id: m
        for m in (await db.execute(select(Malzeme).where(Malzeme.id.in_(malzeme_idler or [0]))))
        .scalars()
        .all()
    }
    return ReceteCevapDTO(
        urun_id=recete.urun_id,
        ad=recete.ad,
        aktif=recete.aktif,
        kalemler=[
            ReceteKalemCevapDTO(
                malzeme_id=k.malzeme_id,
                malzeme_kod=malzemeler[k.malzeme_id].kod if k.malzeme_id in malzemeler else "?",
                malzeme_ad=malzemeler[k.malzeme_id].ad if k.malzeme_id in malzemeler else "?",
                birim=malzemeler[k.malzeme_id].birim if k.malzeme_id in malzemeler else "",
                miktar=float(k.miktar),
            )
            for k in recete.kalemler
        ],
    ).model_dump()


@router.get("/urunler", response_model=Zarf[list[UrunCevapDTO]], summary="Ürünleri listele")
async def urun_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    arama: str | None = None,
    aktif: bool | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kosullar: list[Any] = []
    if arama:
        kosullar.append(Urun.ad.ilike(f"%{arama}%") | Urun.kod.ilike(f"%{arama}%"))
    if aktif is not None:
        kosullar.append(Urun.aktif == aktif)
    toplam = (
        await db.execute(select(func.count()).select_from(Urun).where(*kosullar))
    ).scalar_one()
    kayitlar = (
        (
            await db.execute(
                select(Urun)
                .where(*kosullar)
                .order_by(Urun.id.desc())
                .offset((sayfa - 1) * adet)
                .limit(adet)
            )
        )
        .scalars()
        .all()
    )
    return sayfali([_urun_cevap(u) for u in kayitlar], sayfa=sayfa, adet=adet, toplam=int(toplam))


@router.post("/urunler", response_model=Zarf[UrunCevapDTO], status_code=201, summary="Ürün oluştur")
async def urun_olustur(
    govde: UrunOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    mevcut = (await db.execute(select(Urun.id).where(Urun.kod == govde.kod))).scalar_one_or_none()
    if mevcut is not None:
        raise CakismaHatasi("Bu kod ile ürün zaten var")
    urun = Urun(kod=govde.kod, ad=govde.ad, birim=govde.birim, aciklama=govde.aciklama)
    db.add(urun)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="urun", kaynak_id=str(urun.id), kullanici=kullanici
    )
    return basari(_urun_cevap(urun), mesaj="Ürün oluşturuldu")


@router.get("/urunler/{urun_id}", response_model=Zarf[UrunCevapDTO], summary="Ürün detayı")
async def urun_detay(
    urun_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    urun = await db.get(Urun, urun_id)
    if urun is None:
        raise KaynakBulunamadi("Ürün bulunamadı")
    return basari(_urun_cevap(urun), mesaj="Ürün detayı")


@router.patch("/urunler/{urun_id}", response_model=Zarf[UrunCevapDTO], summary="Ürün düzenle")
async def urun_guncelle(
    urun_id: int,
    govde: UrunGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    urun = await db.get(Urun, urun_id)
    if urun is None:
        raise KaynakBulunamadi("Ürün bulunamadı")
    for alan, deger in govde.model_dump(exclude_unset=True).items():
        if deger is not None:
            setattr(urun, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="urun", kaynak_id=str(urun.id), kullanici=kullanici
    )
    return basari(_urun_cevap(urun), mesaj="Ürün güncellendi")


@router.get(
    "/urunler/{urun_id}/recete",
    response_model=Zarf[ReceteCevapDTO],
    summary="Ürün reçetesi (BOM)",
)
async def recete_getir(
    urun_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if await db.get(Urun, urun_id) is None:
        raise KaynakBulunamadi("Ürün bulunamadı")
    recete = (
        await db.execute(
            select(Recete).options(selectinload(Recete.kalemler)).where(Recete.urun_id == urun_id)
        )
    ).scalar_one_or_none()
    if recete is None:
        # Reçetesiz ürün: boş kalem listesi (404 değil — FE düzenleme başlangıcı).
        bos = ReceteCevapDTO(urun_id=urun_id, ad="", aktif=True, kalemler=[])
        return basari(bos.model_dump(), mesaj="Reçete (boş)")
    return basari(await _recete_cevap(db, recete), mesaj="Reçete")


@router.put(
    "/urunler/{urun_id}/recete",
    response_model=Zarf[ReceteCevapDTO],
    summary="Ürün reçetesini kaydet (replace-all)",
)
async def recete_kaydet(
    urun_id: int,
    govde: ReceteKaydetDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("uretim:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if await db.get(Urun, urun_id) is None:
        raise KaynakBulunamadi("Ürün bulunamadı")
    malzeme_idler = [k.malzeme_id for k in govde.kalemler]
    if len(malzeme_idler) != len(set(malzeme_idler)):
        raise DogrulamaHatasi(
            "Bir malzeme reçetede en fazla bir kez yer alabilir",
            detaylar=[{"alan": "kalemler", "mesaj": "mükerrer malzeme_id"}],
        )
    if malzeme_idler:
        mevcutlar = set(
            (await db.execute(select(Malzeme.id).where(Malzeme.id.in_(malzeme_idler))))
            .scalars()
            .all()
        )
        bilinmeyen = sorted(set(malzeme_idler) - mevcutlar)
        if bilinmeyen:
            raise DogrulamaHatasi(
                "Bilinmeyen malzeme",
                detaylar=[
                    {"alan": "kalemler", "mesaj": f"malzeme_id bulunamadı: {mid}"}
                    for mid in bilinmeyen
                ],
            )
    recete = (
        await db.execute(
            select(Recete).options(selectinload(Recete.kalemler)).where(Recete.urun_id == urun_id)
        )
    ).scalar_one_or_none()
    if recete is None:
        # kalemler=[] koleksiyonu baştan başlatır; flush sonrası append lazy-load
        # tetiklemez (async oturumda MissingGreenlet).
        recete = Recete(urun_id=urun_id, ad=govde.ad, kalemler=[])
        db.add(recete)
        await db.flush()
    else:
        recete.ad = govde.ad
        recete.kalemler.clear()
        await db.flush()
    for kalem in govde.kalemler:
        recete.kalemler.append(ReceteKalemi(malzeme_id=kalem.malzeme_id, miktar=kalem.miktar))
    await db.flush()
    await denetim_yaz(
        db,
        eylem="recete_kaydet",
        kaynak="urun",
        kaynak_id=str(urun_id),
        kullanici=kullanici,
        detay={"kalem_sayisi": len(govde.kalemler)},
    )
    await db.refresh(recete, attribute_names=["kalemler"])
    return basari(await _recete_cevap(db, recete), mesaj="Reçete kaydedildi")
