"""ESG uçları (``/api/v1``, S32 / ADR-0051): okuma ``esg:oku``, faktör yönetimi ``esg:yaz``.

Dönemsel rapor (PDF/XLSX) rapor modülünün async akışından (`POST /raporlar`, tür ``esg``, 202)
üretilir.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari
from app.core.zaman import is_gunu
from app.kimlik.models import Kullanici
from app.modules.enerji.birimler import ENERJI_TURLERI
from app.modules.esg import hesap, service
from app.modules.esg.models import EmisyonFaktoru

router = APIRouter(tags=["ESG"], dependencies=[Depends(modul_gerekli("esg"))])
Oturum = Annotated[AsyncSession, Depends(get_session)]
TenantDep = Annotated[Tenant, Depends(tenant_cozumle)]
Oku = Annotated[Kullanici, Depends(izin_gerekli("esg:oku"))]
Yaz = Annotated[Kullanici, Depends(izin_gerekli("esg:yaz"))]

# Aralık sınırı: günlük kırılımda 3 ay, aylıkta 3 yıl (yanıt boyutu ve sorgu süresi).
_EN_COK_GUN = {"gun": 92, "ay": 1096}


class EsgDonemDTO(BaseModel):
    donem: date
    kapsam1_kg: float
    kapsam2_kg: float
    toplam_kg: float
    elektrik_kwh: float
    saglam_adet: int
    kg_adet: float | None
    kwh_adet: float | None


class EsgTurDTO(BaseModel):
    enerji_turu: str
    birim: str
    miktar: float
    emisyon_kg: float | None
    kapsam: str | None
    faktor: float | None
    faktor_kaynagi: str | None


class EsgOzetDTO(BaseModel):
    baslangic: date
    bitis: date
    donem: str
    kapsam1_ton: float
    kapsam2_ton: float
    toplam_ton: float
    saglam_adet: int
    kg_adet: float | None
    kwh_adet: float | None
    donemler: list[EsgDonemDTO]
    turler: list[EsgTurDTO]
    faktorsuz: list[EsgTurDTO]


class FaktorDTO(BaseModel):
    id: int | None
    enerji_turu: str
    birim: str
    deger: float
    kapsam: str
    gecerlilik: date
    kaynak: str
    koken: str  # tenant | varsayilan


class FaktorOlusturDTO(BaseModel):
    enerji_turu: str = Field(max_length=20)
    birim: str = Field(min_length=1, max_length=20)
    deger: Decimal = Field(ge=0, le=Decimal("100000"), max_digits=14, decimal_places=6)
    kapsam: Literal["kapsam1", "kapsam2"]
    gecerlilik: date
    kaynak: str = Field(min_length=3, max_length=300)


def _tur_dto(t: hesap.TurSonucu, faktorlu: bool) -> EsgTurDTO:
    f = t.faktor
    return EsgTurDTO(
        enerji_turu=t.enerji_turu,
        birim=t.birim,
        miktar=round(float(t.miktar), 3),
        emisyon_kg=round(float(t.emisyon), 3) if faktorlu else None,
        kapsam=f.kapsam if f else None,
        faktor=float(f.deger) if f else None,
        faktor_kaynagi=f.kaynak if f else None,
    )


@router.get("/esg/ozet", response_model=Zarf[EsgOzetDTO], summary="Dönemsel emisyon ve yoğunluk")
async def esg_ozet(
    _k: Oku,
    db: Oturum,
    _t: TenantDep,
    baslangic: date | None = None,
    bitis: date | None = None,
    donem: Literal["gun", "ay"] = "gun",
) -> dict[str, Any]:
    bitis = bitis or is_gunu()
    baslangic = baslangic or (bitis - timedelta(days=29))
    if baslangic > bitis:
        raise DogrulamaHatasi("Başlangıç bitişten sonra olamaz")
    if (bitis - baslangic).days + 1 > _EN_COK_GUN[donem]:
        raise DogrulamaHatasi(
            "Aralık çok uzun",
            detaylar=[{"alan": "baslangic", "mesaj": f"en çok {_EN_COK_GUN[donem]} gün"}],
        )
    r = await service.hesapla(db, baslangic=baslangic, bitis=bitis, donem=donem)
    s = r.sonuc
    toplam_kwh = sum((d.elektrik_kwh for d in s.donemler), Decimal(0))
    kg_adet = hesap.yogunluk(s.toplam, r.toplam_adet)
    kwh_adet = hesap.yogunluk(toplam_kwh, r.toplam_adet)
    return basari(
        EsgOzetDTO(
            baslangic=baslangic,
            bitis=bitis,
            donem=donem,
            kapsam1_ton=service.kg_ton(s.kapsam1),
            kapsam2_ton=service.kg_ton(s.kapsam2),
            toplam_ton=service.kg_ton(s.toplam),
            saglam_adet=r.toplam_adet,
            kg_adet=round(float(kg_adet), 4) if kg_adet is not None else None,
            kwh_adet=round(float(kwh_adet), 4) if kwh_adet is not None else None,
            donemler=[EsgDonemDTO(**x) for x in service.ozet_satirlari(r)],
            turler=[_tur_dto(t, True) for t in s.turler],
            faktorsuz=[_tur_dto(t, False) for t in s.faktorsuz],
        ).model_dump(),
        mesaj="ESG özeti",
    )


@router.get("/esg/faktorler", response_model=Zarf[list[FaktorDTO]], summary="Etkin faktörler")
async def faktor_listele(_k: Oku, db: Oturum, _t: TenantDep) -> dict[str, Any]:
    return basari(
        [
            FaktorDTO(
                id=fid,
                enerji_turu=f.enerji_turu,
                birim=f.birim,
                deger=float(f.deger),
                kapsam=f.kapsam,
                gecerlilik=f.gecerlilik,
                kaynak=f.kaynak,
                koken=koken,
            ).model_dump()
            for f, koken, fid in await service.faktorler(db)
        ],
        mesaj="Faktörler",
    )


@router.post(
    "/esg/faktorler", response_model=Zarf[FaktorDTO], status_code=201, summary="Faktör ekle"
)
async def faktor_ekle(govde: FaktorOlusturDTO, k: Yaz, db: Oturum, _t: TenantDep) -> dict[str, Any]:
    if govde.enerji_turu not in ENERJI_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz enerji türü",
            detaylar=[
                {"alan": "enerji_turu", "mesaj": f"Geçerli: {', '.join(sorted(ENERJI_TURLERI))}"}
            ],
        )
    birim, carpan = hesap.birim_normalle(govde.birim, Decimal(1))
    if carpan != 1:
        raise DogrulamaHatasi(
            "Faktör temel birim başına girilmeli",
            detaylar=[{"alan": "birim", "mesaj": f"{govde.birim} yerine {birim} kullanın"}],
        )
    var = await db.scalar(
        select(EmisyonFaktoru.id).where(
            EmisyonFaktoru.enerji_turu == govde.enerji_turu,
            EmisyonFaktoru.birim == birim,
            EmisyonFaktoru.gecerlilik == govde.gecerlilik,
        )
    )
    if var is not None:
        raise CakismaHatasi("Bu tür, birim ve geçerlilik tarihi için faktör zaten var")
    f = EmisyonFaktoru(
        enerji_turu=govde.enerji_turu,
        birim=birim,
        deger=govde.deger,
        kapsam=govde.kapsam,
        gecerlilik=govde.gecerlilik,
        kaynak=govde.kaynak,
    )
    db.add(f)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="olustur",
        kaynak="emisyon_faktoru",
        kaynak_id=str(f.id),
        kullanici=k,
        detay={"enerji_turu": f.enerji_turu, "birim": birim, "deger": str(govde.deger)},
    )
    return basari(
        FaktorDTO(
            id=f.id,
            enerji_turu=f.enerji_turu,
            birim=f.birim,
            deger=float(f.deger),
            kapsam=f.kapsam,
            gecerlilik=f.gecerlilik,
            kaynak=f.kaynak,
            koken="tenant",
        ).model_dump(),
        mesaj="Faktör eklendi",
    )


@router.delete("/esg/faktorler/{faktor_id}", status_code=204, summary="Faktör sil")
async def faktor_sil(faktor_id: int, k: Yaz, db: Oturum, _t: TenantDep) -> Response:
    f = await db.get(EmisyonFaktoru, faktor_id)
    if f is None:
        raise KaynakBulunamadi("Faktör bulunamadı")
    await db.delete(f)
    await denetim_yaz(
        db, eylem="sil", kaynak="emisyon_faktoru", kaynak_id=str(faktor_id), kullanici=k
    )
    return Response(status_code=204)
