"""S26-A uçları: ölçüm cihazları + kalibrasyon, kontrol planları + SPC kartı (ADR-0025)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari
from app.core.zaman import is_gunu
from app.kimlik.models import Kullanici
from app.modules.kalite import spc_service as servis
from app.modules.kalite.models import (
    CIHAZ_DURUMLARI,
    KALIBRASYON_SONUCLARI,
    KalibrasyonKaydi,
    KontrolKarakteristigi,
    KontrolPlani,
    OlcumCihazi,
)

router = APIRouter(
    tags=["Kalite · SPC & Kalibrasyon"], dependencies=[Depends(modul_gerekli("kalite"))]
)

Oku = Annotated[Kullanici, Depends(izin_gerekli("kalite:oku"))]
Yaz = Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))]
Db = Annotated[AsyncSession, Depends(get_session)]
TenantDep = Annotated[Tenant, Depends(tenant_cozumle)]


# ── DTO ──────────────────────────────────────────────────────────────────────


class OlcumCihaziOlusturDTO(BaseModel):
    kod: str = Field(min_length=1, max_length=50)
    ad: str = Field(min_length=1, max_length=200)
    tur: str = Field(default="", max_length=100)
    seri_no: str = Field(default="", max_length=100)
    konum: str = Field(default="", max_length=200)
    kalibrasyon_periyodu_gun: int = Field(default=365, ge=1, le=3650)
    sorumlu_kullanici_id: int | None = None


class OlcumCihaziGuncelleDTO(BaseModel):
    ad: str | None = Field(default=None, min_length=1, max_length=200)
    konum: str | None = Field(default=None, max_length=200)
    kalibrasyon_periyodu_gun: int | None = Field(default=None, ge=1, le=3650)
    durum: str | None = None
    sorumlu_kullanici_id: int | None = None


class OlcumCihaziDTO(BaseModel):
    id: int
    kod: str
    ad: str
    tur: str
    seri_no: str
    konum: str
    kalibrasyon_periyodu_gun: int
    son_kalibrasyon_tarihi: date | None
    sonraki_kalibrasyon_tarihi: date | None
    durum: str
    gecerlilik: str
    kalan_gun: int | None
    sorumlu_kullanici_id: int | None


class KalibrasyonOlusturDTO(BaseModel):
    tarih: date
    sonuc: str
    sertifika_no: str = Field(default="", max_length=100)
    kurum: str = Field(default="", max_length=200)
    aciklama: str = Field(default="", max_length=1000)
    belge_id: int | None = None


class KalibrasyonDTO(BaseModel):
    id: int
    tarih: date
    sonuc: str
    sertifika_no: str
    kurum: str
    aciklama: str
    belge_id: int | None
    kaydeden_kullanici_id: int | None


class OlcumCihaziDetayDTO(OlcumCihaziDTO):
    kalibrasyonlar: list[KalibrasyonDTO]


class TaraDTO(BaseModel):
    esik_gun: int = Field(default=30, ge=1, le=365)


class KarakteristikOlusturDTO(BaseModel):
    ad: str = Field(min_length=1, max_length=200)
    birim: str = Field(default="mm", max_length=20)
    nominal: Decimal | None = None
    alt_tolerans: Decimal | None = None
    ust_tolerans: Decimal | None = None
    alt_grup_boyutu: int = Field(default=5, ge=2, le=10)
    olcum_yontemi: str = Field(default="", max_length=500)
    cihaz_id: int | None = None


class KarakteristikDTO(KarakteristikOlusturDTO):
    id: int
    sira: int
    limitler_sabit: bool
    alt_grup_sayisi: int = 0
    son_ihlal: bool = False


class KontrolPlaniOlusturDTO(BaseModel):
    ad: str = Field(min_length=1, max_length=200)
    urun_id: int | None = None
    operasyon: str = Field(default="", max_length=200)
    aciklama: str = Field(default="", max_length=1000)
    karakteristikler: list[KarakteristikOlusturDTO] = Field(default_factory=list, max_length=50)


class KontrolPlaniDTO(BaseModel):
    id: int
    kod: str
    ad: str
    urun_id: int | None
    operasyon: str
    aciklama: str
    aktif: bool
    karakteristik_sayisi: int


class KontrolPlaniDetayDTO(KontrolPlaniDTO):
    karakteristikler: list[KarakteristikDTO]


class OlcumDTO(BaseModel):
    degerler: list[float] = Field(min_length=2, max_length=10)
    cihaz_id: int | None = None
    aciklama: str = Field(default="", max_length=500)


class SabitleDTO(BaseModel):
    ilk: int | None = Field(default=None, ge=2)


# ── Yardımcılar ──────────────────────────────────────────────────────────────


def _cihaz(c: OlcumCihazi) -> dict[str, Any]:
    bugun = is_gunu()
    return OlcumCihaziDTO(
        id=c.id,
        kod=c.kod,
        ad=c.ad,
        tur=c.tur,
        seri_no=c.seri_no,
        konum=c.konum,
        kalibrasyon_periyodu_gun=c.kalibrasyon_periyodu_gun,
        son_kalibrasyon_tarihi=c.son_kalibrasyon_tarihi,
        sonraki_kalibrasyon_tarihi=c.sonraki_kalibrasyon_tarihi,
        durum=c.durum,
        gecerlilik=servis.cihaz_durum_etiketi(c, bugun),
        kalan_gun=(c.sonraki_kalibrasyon_tarihi - bugun).days
        if c.sonraki_kalibrasyon_tarihi
        else None,
        sorumlu_kullanici_id=c.sorumlu_kullanici_id,
    ).model_dump()


async def _karakteristik(db: AsyncSession, k: KontrolKarakteristigi) -> dict[str, Any]:
    kart = await servis.kart(db, k)
    son = kart["noktalar"][-1] if kart["noktalar"] else None
    return KarakteristikDTO(
        id=k.id,
        sira=k.sira,
        ad=k.ad,
        birim=k.birim,
        nominal=k.nominal,
        alt_tolerans=k.alt_tolerans,
        ust_tolerans=k.ust_tolerans,
        alt_grup_boyutu=k.alt_grup_boyutu,
        olcum_yontemi=k.olcum_yontemi,
        cihaz_id=k.cihaz_id,
        limitler_sabit=bool(k.sabit_limitler),
        alt_grup_sayisi=len(kart["noktalar"]),
        son_ihlal=bool(son and son["kayitli_ihlaller"]),
    ).model_dump()


async def _plan_detay(db: AsyncSession, p: KontrolPlani) -> dict[str, Any]:
    return KontrolPlaniDetayDTO(
        id=p.id,
        kod=p.kod,
        ad=p.ad,
        urun_id=p.urun_id,
        operasyon=p.operasyon,
        aciklama=p.aciklama,
        aktif=p.aktif,
        karakteristik_sayisi=len(p.karakteristikler),
        karakteristikler=[
            KarakteristikDTO(**await _karakteristik(db, k)) for k in p.karakteristikler
        ],
    ).model_dump()


async def _cihaz_var(db: AsyncSession, cihaz_id: int | None) -> None:
    if cihaz_id is not None and await db.get(OlcumCihazi, cihaz_id) is None:
        raise KaynakBulunamadi("Ölçüm cihazı bulunamadı")


# ── Ölçüm cihazları ──────────────────────────────────────────────────────────


@router.get(
    "/olcum-cihazlari", response_model=Zarf[list[OlcumCihaziDTO]], summary="Ölçüm cihazları"
)
async def cihazlar(_k: Oku, db: Db) -> dict[str, Any]:
    satirlar = (await db.execute(select(OlcumCihazi).order_by(OlcumCihazi.kod))).scalars().all()
    return basari([_cihaz(c) for c in satirlar])


@router.post(
    "/olcum-cihazlari", response_model=Zarf[OlcumCihaziDTO], status_code=201, summary="Cihaz ekle"
)
async def cihaz_olustur(govde: OlcumCihaziOlusturDTO, kullanici: Yaz, db: Db) -> dict[str, Any]:
    if (await db.execute(select(OlcumCihazi.id).where(OlcumCihazi.kod == govde.kod))).first():
        raise CakismaHatasi("Bu kodla bir cihaz zaten var", hata_kodu="KOD_VAR")
    c = OlcumCihazi(**govde.model_dump())
    db.add(c)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="olcum_cihazi", kaynak_id=str(c.id), kullanici=kullanici
    )
    return basari(_cihaz(c), mesaj="Cihaz eklendi")


@router.get(
    "/olcum-cihazlari/{cihaz_id}", response_model=Zarf[OlcumCihaziDetayDTO], summary="Cihaz detayı"
)
async def cihaz_detay(cihaz_id: int, _k: Oku, db: Db) -> dict[str, Any]:
    c = await db.get(OlcumCihazi, cihaz_id)
    if c is None:
        raise KaynakBulunamadi("Ölçüm cihazı bulunamadı")
    kayitlar = (
        (
            await db.execute(
                select(KalibrasyonKaydi)
                .where(KalibrasyonKaydi.cihaz_id == c.id)
                .order_by(KalibrasyonKaydi.tarih.desc(), KalibrasyonKaydi.id.desc())
            )
        )
        .scalars()
        .all()
    )
    return basari(
        {
            **_cihaz(c),
            "kalibrasyonlar": [
                KalibrasyonDTO.model_validate(k, from_attributes=True).model_dump()
                for k in kayitlar
            ],
        }
    )


@router.patch(
    "/olcum-cihazlari/{cihaz_id}", response_model=Zarf[OlcumCihaziDTO], summary="Cihaz güncelle"
)
async def cihaz_guncelle(
    cihaz_id: int, govde: OlcumCihaziGuncelleDTO, kullanici: Yaz, db: Db
) -> dict[str, Any]:
    c = await db.get(OlcumCihazi, cihaz_id)
    if c is None:
        raise KaynakBulunamadi("Ölçüm cihazı bulunamadı")
    veri = govde.model_dump(exclude_unset=True)
    if "durum" in veri and veri["durum"] not in CIHAZ_DURUMLARI:
        raise CakismaHatasi(f"Geçerli durumlar: {', '.join(sorted(CIHAZ_DURUMLARI))}")
    if veri.get("durum") == "aktif" and c.durum == "kullanim_disi":
        # Uygunsuz kalibrasyondan sonra cihaz elle aktif edilemez; yeni kalibrasyon kaydı gerekir.
        raise CakismaHatasi(
            "Kullanım dışı cihaz yalnız yeni bir kalibrasyon kaydıyla aktif olur",
            hata_kodu="KALIBRASYON_GEREKLI",
        )
    for alan, deger in veri.items():
        setattr(c, alan, deger)
    if "kalibrasyon_periyodu_gun" in veri and c.son_kalibrasyon_tarihi and c.durum == "aktif":
        c.sonraki_kalibrasyon_tarihi = c.son_kalibrasyon_tarihi + timedelta(
            days=c.kalibrasyon_periyodu_gun
        )
    await db.flush()
    await denetim_yaz(
        db,
        eylem="guncelle",
        kaynak="olcum_cihazi",
        kaynak_id=str(c.id),
        kullanici=kullanici,
        detay=veri,
    )
    return basari(_cihaz(c), mesaj="Cihaz güncellendi")


@router.post(
    "/olcum-cihazlari/{cihaz_id}/kalibrasyonlar",
    response_model=Zarf[OlcumCihaziDTO],
    status_code=201,
    summary="Kalibrasyon kaydı ekle",
)
async def kalibrasyon_ekle(
    cihaz_id: int, govde: KalibrasyonOlusturDTO, kullanici: Yaz, db: Db
) -> dict[str, Any]:
    if govde.sonuc not in KALIBRASYON_SONUCLARI:
        raise CakismaHatasi(f"Geçerli sonuçlar: {', '.join(sorted(KALIBRASYON_SONUCLARI))}")
    c = (
        await db.execute(select(OlcumCihazi).where(OlcumCihazi.id == cihaz_id).with_for_update())
    ).scalar_one_or_none()
    if c is None:
        raise KaynakBulunamadi("Ölçüm cihazı bulunamadı")
    kayit = await servis.kalibrasyon_ekle(db, c, kullanici=kullanici, **govde.model_dump())
    await denetim_yaz(
        db,
        eylem="kalibrasyon",
        kaynak="olcum_cihazi",
        kaynak_id=str(c.id),
        kullanici=kullanici,
        detay={"kayit_id": kayit.id, "sonuc": kayit.sonuc, "tarih": kayit.tarih.isoformat()},
    )
    return basari(_cihaz(c), mesaj="Kalibrasyon kaydedildi")


@router.post(
    "/olcum-cihazlari/kalibrasyon-tara",
    response_model=Zarf[dict[str, int]],
    summary="Yaklaşan kalibrasyonları bildir",
)
async def kalibrasyon_tara(govde: TaraDTO, _k: Yaz, db: Db, tenant: TenantDep) -> dict[str, Any]:
    adet = await servis.kalibrasyon_tara(db, tenant_slug=tenant.slug, esik_gun=govde.esik_gun)
    return basari({"bildirilen": adet})


# ── Kontrol planları ─────────────────────────────────────────────────────────


@router.get(
    "/kontrol-planlari", response_model=Zarf[list[KontrolPlaniDTO]], summary="Kontrol planları"
)
async def planlar(
    _k: Oku, db: Db, urun_id: Annotated[int | None, Query()] = None
) -> dict[str, Any]:
    sorgu = select(KontrolPlani).order_by(KontrolPlani.kod)
    if urun_id is not None:
        sorgu = sorgu.where(KontrolPlani.urun_id == urun_id)
    planlar_ = (await db.execute(sorgu)).scalars().all()
    sayilar: dict[int, int] = {}
    for (pid,) in (await db.execute(select(KontrolKarakteristigi.plan_id))).all():
        sayilar[pid] = sayilar.get(pid, 0) + 1
    return basari(
        [
            KontrolPlaniDTO(
                id=p.id,
                kod=p.kod,
                ad=p.ad,
                urun_id=p.urun_id,
                operasyon=p.operasyon,
                aciklama=p.aciklama,
                aktif=p.aktif,
                karakteristik_sayisi=sayilar.get(p.id, 0),
            ).model_dump()
            for p in planlar_
        ]
    )


@router.post(
    "/kontrol-planlari",
    response_model=Zarf[KontrolPlaniDetayDTO],
    status_code=201,
    summary="Kontrol planı oluştur",
)
async def plan_olustur(govde: KontrolPlaniOlusturDTO, kullanici: Yaz, db: Db) -> dict[str, Any]:
    for k in govde.karakteristikler:
        servis.karakteristik_dogrula(k.alt_tolerans, k.ust_tolerans, k.alt_grup_boyutu)
        await _cihaz_var(db, k.cihaz_id)
    p = KontrolPlani(
        kod=f"GECICI-{datetime.now(UTC).timestamp():.0f}",
        ad=govde.ad,
        urun_id=govde.urun_id,
        operasyon=govde.operasyon,
        aciklama=govde.aciklama,
        olusturan_kullanici_id=kullanici.id,
    )
    db.add(p)
    await db.flush()
    p.kod = servis.plan_kodu(p.id)
    for i, k in enumerate(govde.karakteristikler, start=1):
        db.add(KontrolKarakteristigi(plan_id=p.id, sira=i, **k.model_dump()))
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="kontrol_plani", kaynak_id=str(p.id), kullanici=kullanici
    )
    return basari(
        await _plan_detay(db, await servis.plan_getir(db, p.id)), mesaj="Kontrol planı oluşturuldu"
    )


@router.get(
    "/kontrol-planlari/{plan_id}",
    response_model=Zarf[KontrolPlaniDetayDTO],
    summary="Kontrol planı detayı",
)
async def plan_detay(plan_id: int, _k: Oku, db: Db) -> dict[str, Any]:
    return basari(await _plan_detay(db, await servis.plan_getir(db, plan_id)))


@router.post(
    "/kontrol-planlari/{plan_id}/karakteristikler",
    response_model=Zarf[KontrolPlaniDetayDTO],
    status_code=201,
    summary="Plana karakteristik ekle",
)
async def karakteristik_ekle(
    plan_id: int, govde: KarakteristikOlusturDTO, kullanici: Yaz, db: Db
) -> dict[str, Any]:
    p = await servis.plan_getir(db, plan_id)
    servis.karakteristik_dogrula(govde.alt_tolerans, govde.ust_tolerans, govde.alt_grup_boyutu)
    await _cihaz_var(db, govde.cihaz_id)
    db.add(
        KontrolKarakteristigi(plan_id=p.id, sira=len(p.karakteristikler) + 1, **govde.model_dump())
    )
    await db.flush()
    await denetim_yaz(
        db,
        eylem="karakteristik_ekle",
        kaynak="kontrol_plani",
        kaynak_id=str(p.id),
        kullanici=kullanici,
    )
    db.expire(p)
    return basari(await _plan_detay(db, await servis.plan_getir(db, p.id)))


# ── SPC ──────────────────────────────────────────────────────────────────────


@router.get(
    "/karakteristikler/{karakteristik_id}/kart",
    response_model=Zarf[dict[str, Any]],
    summary="SPC kartı (X̄-R)",
)
async def spc_kart(karakteristik_id: int, _k: Oku, db: Db) -> dict[str, Any]:
    k = await db.get(KontrolKarakteristigi, karakteristik_id)
    if k is None:
        raise KaynakBulunamadi("Karakteristik bulunamadı")
    return basari(await servis.kart(db, k))


@router.post(
    "/karakteristikler/{karakteristik_id}/olcumler",
    response_model=Zarf[dict[str, Any]],
    status_code=201,
    summary="SPC alt grubu (ölçüm) gir",
)
async def spc_olcum(
    karakteristik_id: int, govde: OlcumDTO, kullanici: Yaz, db: Db, tenant: TenantDep
) -> dict[str, Any]:
    grup, ihlaller = await servis.olcum_ekle(
        db,
        karakteristik_id,
        degerler=govde.degerler,
        cihaz_id=govde.cihaz_id,
        aciklama=govde.aciklama,
        kullanici=kullanici,
        tenant_slug=tenant.slug,
    )
    mesaj = f"Ölçüm kaydedildi; {len(ihlaller)} kural ihlali" if ihlaller else "Ölçüm kaydedildi"
    return basari({"sira": grup.sira, "ihlaller": grup.ihlaller}, mesaj=mesaj)


@router.post(
    "/karakteristikler/{karakteristik_id}/limitleri-sabitle",
    response_model=Zarf[dict[str, Any]],
    summary="Kontrol limitlerini sabitle (faz-I)",
)
async def spc_sabitle(
    karakteristik_id: int, govde: SabitleDTO, kullanici: Yaz, db: Db
) -> dict[str, Any]:
    k = await servis.limitleri_sabitle(db, karakteristik_id, ilk=govde.ilk, kullanici=kullanici)
    await denetim_yaz(
        db,
        eylem="spc_limit_sabitle",
        kaynak="kontrol_karakteristigi",
        kaynak_id=str(k.id),
        kullanici=kullanici,
        detay={"alt_grup_sayisi": (k.sabit_limitler or {}).get("alt_grup_sayisi")},
    )
    return basari(await servis.kart(db, k), mesaj="Limitler sabitlendi")
