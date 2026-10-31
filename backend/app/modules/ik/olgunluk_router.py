"""S26-B İK uçları: izin bakiyesi, yönetici ataması + org şeması, kontrol listeleri (ADR-0044)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import KaynakBulunamadi
from app.core.responses import Zarf, basari
from app.kimlik.models import Kullanici
from app.modules.ik import olgunluk as servis
from app.modules.ik.models import Personel, PersonelKontrolListesi

router = APIRouter(
    tags=["İK · Bakiye, Org şeması, Kontrol listesi"],
    dependencies=[Depends(modul_gerekli("ik")), Depends(tenant_cozumle)],
)

Oku = Annotated[Kullanici, Depends(izin_gerekli("ik:oku"))]
Yaz = Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))]
Db = Annotated[AsyncSession, Depends(get_session)]


class HakedisSatiriDTO(BaseModel):
    hizmet_yili: int
    dogdugu_tarih: date
    gun: int


class IzinBakiyesiDTO(BaseModel):
    personel_id: int
    hakedilen: int
    kullanilan: int
    bakiye: int
    kidem_yili: int
    sonraki_hak_tarihi: date | None
    sonraki_hak_gun: int
    satirlar: list[HakedisSatiriDTO]


class YoneticiDTO(BaseModel):
    yonetici_id: int | None = None


class OrgDugumDTO(BaseModel):
    id: int
    ad_soyad: str
    unvan: str
    departman: str
    yonetici_id: int | None
    ast_sayisi: int


class KontrolMaddesiDTO(BaseModel):
    anahtar: str
    ad: str
    tamam: bool
    tamamlayan_kullanici_id: int | None = None
    zaman: datetime | None = None


class KontrolListesiDTO(BaseModel):
    id: int
    personel_id: int
    tur: str
    durum: str
    maddeler: list[KontrolMaddesiDTO]
    tamamlanan: int
    toplam: int
    tamamlanma_tarihi: datetime | None
    acik_zimmet: int


class ListeAcDTO(BaseModel):
    tur: str = Field(pattern="^(giris|cikis)$")


class MaddeDTO(BaseModel):
    tamam: bool


async def _personel(db: AsyncSession, personel_id: int) -> Personel:
    p = await db.get(Personel, personel_id)
    if p is None:
        raise KaynakBulunamadi("Personel bulunamadı")
    return p


async def _liste_cevap(db: AsyncSession, liste: PersonelKontrolListesi) -> dict[str, Any]:
    return KontrolListesiDTO(
        id=liste.id,
        personel_id=liste.personel_id,
        tur=liste.tur,
        durum=liste.durum,
        maddeler=[KontrolMaddesiDTO(**m) for m in liste.maddeler],
        tamamlanan=sum(1 for m in liste.maddeler if m["tamam"]),
        toplam=len(liste.maddeler),
        tamamlanma_tarihi=liste.tamamlanma_tarihi,
        acik_zimmet=await servis.acik_zimmet_sayisi(db, liste.personel_id),
    ).model_dump()


@router.get(
    "/personeller/{personel_id}/izin-bakiyesi",
    response_model=Zarf[IzinBakiyesiDTO],
    summary="Yıllık izin hakedişi ve bakiyesi",
)
async def izin_bakiyesi(personel_id: int, _k: Oku, db: Db) -> dict[str, Any]:
    p = await _personel(db, personel_id)
    b = await servis.bakiye_hesapla(db, p)
    return basari(
        IzinBakiyesiDTO(
            personel_id=p.id,
            hakedilen=b.hakedilen,
            kullanilan=b.kullanilan,
            bakiye=b.bakiye,
            kidem_yili=b.kidem_yili,
            sonraki_hak_tarihi=b.sonraki_hak_tarihi,
            sonraki_hak_gun=b.sonraki_hak_gun,
            satirlar=[HakedisSatiriDTO(**vars(s)) for s in b.satirlar],
        ).model_dump(),
        mesaj="İzin bakiyesi",
    )


@router.put(
    "/personeller/{personel_id}/yonetici",
    response_model=Zarf[YoneticiDTO],
    summary="Doğrudan yönetici ata / kaldır",
)
async def yonetici_ata(personel_id: int, govde: YoneticiDTO, k: Yaz, db: Db) -> dict[str, Any]:
    p = await _personel(db, personel_id)
    await servis.yonetici_ata(db, p, govde.yonetici_id)
    await denetim_yaz(
        db,
        eylem="guncelle",
        kaynak="personel",
        kaynak_id=str(p.id),
        kullanici=k,
        detay={"yonetici_id": p.yonetici_id},
    )
    return basari(YoneticiDTO(yonetici_id=p.yonetici_id).model_dump(), mesaj="Yönetici atandı")


@router.get("/ik/org-semasi", response_model=Zarf[list[OrgDugumDTO]], summary="Org şeması")
async def org_semasi(_k: Oku, db: Db, departman: str | None = None) -> dict[str, Any]:
    return basari(await servis.org_semasi(db, departman), mesaj="Org şeması")


@router.get(
    "/personeller/{personel_id}/kontrol-listeleri",
    response_model=Zarf[list[KontrolListesiDTO]],
    summary="Personelin işe giriş / çıkış kontrol listeleri",
)
async def kontrol_listeleri(personel_id: int, _k: Oku, db: Db) -> dict[str, Any]:
    await _personel(db, personel_id)
    listeler = (
        (
            await db.execute(
                select(PersonelKontrolListesi)
                .where(PersonelKontrolListesi.personel_id == personel_id)
                .order_by(PersonelKontrolListesi.tur.desc())
            )
        )
        .scalars()
        .all()
    )
    return basari([await _liste_cevap(db, li) for li in listeler], mesaj="Kontrol listeleri")


@router.post(
    "/personeller/{personel_id}/kontrol-listeleri",
    response_model=Zarf[KontrolListesiDTO],
    summary="Kontrol listesi aç (varsa olanı döner)",
)
async def kontrol_listesi_ac(personel_id: int, govde: ListeAcDTO, k: Yaz, db: Db) -> dict[str, Any]:
    p = await _personel(db, personel_id)
    liste = await servis.liste_ac(db, p, govde.tur)
    await denetim_yaz(
        db, eylem="olustur", kaynak="kontrol_listesi", kaynak_id=str(liste.id), kullanici=k
    )
    return basari(await _liste_cevap(db, liste), mesaj="Kontrol listesi")


@router.put(
    "/kontrol-listeleri/{liste_id}/maddeler/{anahtar}",
    response_model=Zarf[KontrolListesiDTO],
    summary="Kontrol maddesini işaretle / geri al",
)
async def madde_isaretle(
    liste_id: int, anahtar: str, govde: MaddeDTO, k: Yaz, db: Db
) -> dict[str, Any]:
    liste = await db.scalar(
        select(PersonelKontrolListesi)
        .where(PersonelKontrolListesi.id == liste_id)
        .with_for_update()
    )
    if liste is None:
        raise KaynakBulunamadi("Kontrol listesi bulunamadı")
    await servis.madde_isaretle(db, liste, anahtar, govde.tamam, k)
    await denetim_yaz(
        db,
        eylem="guncelle",
        kaynak="kontrol_listesi",
        kaynak_id=str(liste.id),
        kullanici=k,
        detay={"madde": anahtar, "tamam": govde.tamam, "durum": liste.durum},
    )
    return basari(await _liste_cevap(db, liste), mesaj="Madde güncellendi")
