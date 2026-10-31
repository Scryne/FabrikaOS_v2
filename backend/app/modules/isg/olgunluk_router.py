"""S26-B İSG uçları: eğitim matrisi, gereksinimler, KKD eksikleri, tatbikat, kaza → CAPA."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari
from app.kimlik.models import Kullanici
from app.modules.ik.models import Personel
from app.modules.isg import olgunluk as servis
from app.modules.isg.egitim_matrisi import ay_ekle
from app.modules.isg.models import (
    AcilDurumTatbikati,
    EgitimGereksinimi,
    EgitimKatilimi,
    IsgEgitimi,
    IsKazasi,
    KkdGereksinimi,
)

router = APIRouter(
    tags=["İSG · Eğitim, KKD, Tatbikat"],
    dependencies=[Depends(modul_gerekli("isg")), Depends(tenant_cozumle)],
)

Oku = Annotated[Kullanici, Depends(izin_gerekli("isg:oku"))]
Yaz = Annotated[Kullanici, Depends(izin_gerekli("isg:yaz"))]
Db = Annotated[AsyncSession, Depends(get_session)]


# ── DTO ──────────────────────────────────────────────────────────────────────


class EgitimOlusturDTO(BaseModel):
    konu: str = Field(min_length=1, max_length=100)
    baslik: str = Field(min_length=1, max_length=200)
    tarih: date
    sure_saat: Decimal = Field(default=Decimal("0"), ge=0, le=999)
    egitmen: str = Field(default="", max_length=200)
    gecerlilik_ay: int = Field(default=12, ge=0, le=120)
    aciklama: str = Field(default="", max_length=2000)
    personel_idler: list[int] = Field(default_factory=list, max_length=500)


class KatilimcilarDTO(BaseModel):
    personel_idler: list[int] = Field(max_length=500)


class KatilimciDTO(BaseModel):
    personel_id: int
    ad_soyad: str
    departman: str


class EgitimDTO(BaseModel):
    id: int
    kod: str
    konu: str
    baslik: str
    tarih: date
    sure_saat: float
    egitmen: str
    gecerlilik_ay: int
    gecerlilik_sonu: date | None
    aciklama: str
    katilimci_sayisi: int


class EgitimDetayDTO(EgitimDTO):
    katilimcilar: list[KatilimciDTO]


class MatrisHucreDTO(BaseModel):
    durum: str
    son_tarih: date | None = None
    gecerlilik_sonu: date | None = None


class MatrisSatirDTO(BaseModel):
    personel_id: int
    ad_soyad: str
    departman: str
    hucreler: dict[str, MatrisHucreDTO]


class MatrisDTO(BaseModel):
    konular: list[str]
    personeller: list[MatrisSatirDTO]
    ozet: dict[str, int]


class GereksinimOlusturDTO(BaseModel):
    departman: str = Field(default="", max_length=100)
    ad: str = Field(min_length=1, max_length=200)


class GereksinimDTO(BaseModel):
    id: int
    departman: str
    ad: str


class KkdEksikDTO(BaseModel):
    personel_id: int
    ad_soyad: str
    departman: str
    gerekli: list[str]
    eksik: list[str]


class TatbikatOlusturDTO(BaseModel):
    tur: str = Field(min_length=1, max_length=30)
    tarih: date
    yer: str = Field(default="", max_length=200)
    katilimci_sayisi: int = Field(default=0, ge=0, le=100000)
    tahliye_suresi_sn: int | None = Field(default=None, ge=0, le=86400)
    bulgular: str = Field(default="", max_length=4000)
    sonraki_tarih: date | None = None


class TatbikatGuncelleDTO(BaseModel):
    yer: str | None = Field(default=None, max_length=200)
    katilimci_sayisi: int | None = Field(default=None, ge=0, le=100000)
    tahliye_suresi_sn: int | None = Field(default=None, ge=0, le=86400)
    bulgular: str | None = Field(default=None, max_length=4000)
    sonraki_tarih: date | None = None


class TatbikatDTO(BaseModel):
    id: int
    kod: str
    tur: str
    tarih: date
    yer: str
    katilimci_sayisi: int
    tahliye_suresi_sn: int | None
    bulgular: str
    sonraki_tarih: date | None
    yurutucu_kullanici_id: int | None


class CapaAcDTO(BaseModel):
    sorumlu_kullanici_id: int | None = None


class KazaCapaDTO(BaseModel):
    uygunsuzluk_id: int
    kod: str
    durum: str
    onem: str


# ── Yardımcılar ──────────────────────────────────────────────────────────────


async def _egitim_cevap(db: AsyncSession, e: IsgEgitimi, detay: bool = False) -> dict[str, Any]:
    katilimcilar = (
        await db.execute(
            select(Personel.id, Personel.ad, Personel.soyad, Personel.departman)
            .join(EgitimKatilimi, EgitimKatilimi.personel_id == Personel.id)
            .where(EgitimKatilimi.egitim_id == e.id)
            .order_by(Personel.ad, Personel.soyad)
        )
    ).all()
    taban = {
        "id": e.id,
        "kod": e.kod,
        "konu": e.konu,
        "baslik": e.baslik,
        "tarih": e.tarih,
        "sure_saat": float(e.sure_saat),
        "egitmen": e.egitmen,
        "gecerlilik_ay": e.gecerlilik_ay,
        "gecerlilik_sonu": ay_ekle(e.tarih, e.gecerlilik_ay) if e.gecerlilik_ay else None,
        "aciklama": e.aciklama,
        "katilimci_sayisi": len(katilimcilar),
    }
    if not detay:
        return EgitimDTO(**taban).model_dump()
    return EgitimDetayDTO(
        **taban,
        katilimcilar=[
            KatilimciDTO(personel_id=i, ad_soyad=f"{a} {s}", departman=d)
            for i, a, s, d in katilimcilar
        ],
    ).model_dump()


async def _katilimci_dogrula(db: AsyncSession, idler: list[int]) -> set[int]:
    istenen = set(idler)
    if not istenen:
        return istenen
    bulunan = set((await db.execute(select(Personel.id).where(Personel.id.in_(istenen)))).scalars())
    eksik = istenen - bulunan
    if eksik:
        raise DogrulamaHatasi(
            "Bilinmeyen personel",
            detaylar=[{"alan": "personel_idler", "mesaj": ", ".join(map(str, sorted(eksik)))}],
        )
    return istenen


def _tatbikat_cevap(t: AcilDurumTatbikati) -> dict[str, Any]:
    return TatbikatDTO(
        id=t.id,
        kod=t.kod,
        tur=t.tur,
        tarih=t.tarih,
        yer=t.yer,
        katilimci_sayisi=t.katilimci_sayisi,
        tahliye_suresi_sn=t.tahliye_suresi_sn,
        bulgular=t.bulgular,
        sonraki_tarih=t.sonraki_tarih,
        yurutucu_kullanici_id=t.yurutucu_kullanici_id,
    ).model_dump()


# ── Eğitimler ────────────────────────────────────────────────────────────────


@router.get("/isg/egitimler", response_model=Zarf[list[EgitimDTO]], summary="İSG eğitimleri")
async def egitimler(_k: Oku, db: Db, konu: str | None = None) -> dict[str, Any]:
    sorgu = select(IsgEgitimi).order_by(IsgEgitimi.tarih.desc(), IsgEgitimi.id.desc())
    if konu:
        sorgu = sorgu.where(IsgEgitimi.konu == konu)
    kayitlar = (await db.execute(sorgu.limit(500))).scalars().all()
    return basari([await _egitim_cevap(db, e) for e in kayitlar], mesaj="Eğitimler")


@router.post(
    "/isg/egitimler",
    response_model=Zarf[EgitimDetayDTO],
    status_code=201,
    summary="Eğitim kaydı (katılımcılarla)",
)
async def egitim_olustur(govde: EgitimOlusturDTO, k: Yaz, db: Db) -> dict[str, Any]:
    katilimcilar = await _katilimci_dogrula(db, govde.personel_idler)
    e = IsgEgitimi(
        kod=f"GECICI-{uuid.uuid4().hex}",
        konu=govde.konu.strip(),
        baslik=govde.baslik,
        tarih=govde.tarih,
        sure_saat=govde.sure_saat,
        egitmen=govde.egitmen,
        gecerlilik_ay=govde.gecerlilik_ay,
        aciklama=govde.aciklama,
    )
    db.add(e)
    await db.flush()
    e.kod = servis.yillik_kod("EGT", e.id)
    db.add_all(EgitimKatilimi(egitim_id=e.id, personel_id=p) for p in sorted(katilimcilar))
    await db.flush()
    await denetim_yaz(db, eylem="olustur", kaynak="isg_egitimi", kaynak_id=str(e.id), kullanici=k)
    return basari(await _egitim_cevap(db, e, detay=True), mesaj="Eğitim kaydedildi")


@router.get(
    "/isg/egitimler/{egitim_id}", response_model=Zarf[EgitimDetayDTO], summary="Eğitim detayı"
)
async def egitim_detay(egitim_id: int, _k: Oku, db: Db) -> dict[str, Any]:
    e = await db.get(IsgEgitimi, egitim_id)
    if e is None:
        raise KaynakBulunamadi("Eğitim bulunamadı")
    return basari(await _egitim_cevap(db, e, detay=True), mesaj="Eğitim detayı")


@router.put(
    "/isg/egitimler/{egitim_id}/katilimcilar",
    response_model=Zarf[EgitimDetayDTO],
    summary="Katılımcı listesini değiştir",
)
async def katilimcilari_degistir(
    egitim_id: int, govde: KatilimcilarDTO, k: Yaz, db: Db
) -> dict[str, Any]:
    e = await db.get(IsgEgitimi, egitim_id, with_for_update=True)
    if e is None:
        raise KaynakBulunamadi("Eğitim bulunamadı")
    istenen = await _katilimci_dogrula(db, govde.personel_idler)
    await db.execute(
        delete(EgitimKatilimi).where(
            EgitimKatilimi.egitim_id == e.id, EgitimKatilimi.personel_id.notin_(istenen or {0})
        )
    )
    mevcut = set(
        (
            await db.execute(
                select(EgitimKatilimi.personel_id).where(EgitimKatilimi.egitim_id == e.id)
            )
        ).scalars()
    )
    db.add_all(EgitimKatilimi(egitim_id=e.id, personel_id=p) for p in sorted(istenen - mevcut))
    await db.flush()
    await denetim_yaz(
        db,
        eylem="guncelle",
        kaynak="isg_egitimi",
        kaynak_id=str(e.id),
        kullanici=k,
        detay={"katilimci_sayisi": len(istenen)},
    )
    return basari(await _egitim_cevap(db, e, detay=True), mesaj="Katılımcılar güncellendi")


@router.get("/isg/egitim-matrisi", response_model=Zarf[MatrisDTO], summary="Eğitim matrisi")
async def egitim_matrisi(_k: Oku, db: Db, departman: str | None = None) -> dict[str, Any]:
    return basari(await servis.egitim_matrisi(db, departman=departman), mesaj="Eğitim matrisi")


# ── Gereksinimler (eğitim konusu / KKD) ──────────────────────────────────────

_GEREKSINIM = {"egitim": (EgitimGereksinimi, "konu"), "kkd": (KkdGereksinimi, "kkd")}


def _gereksinim_modeli(tur: str) -> tuple[Any, str]:
    if tur not in _GEREKSINIM:
        raise KaynakBulunamadi("Gereksinim türü bulunamadı")
    return _GEREKSINIM[tur]


@router.get(
    "/isg/gereksinimler/{tur}",
    response_model=Zarf[list[GereksinimDTO]],
    summary="Departman gereksinimleri (egitim | kkd)",
)
async def gereksinimler(tur: str, _k: Oku, db: Db) -> dict[str, Any]:
    model, alan = _gereksinim_modeli(tur)
    kayitlar: Sequence[Any] = (
        (await db.execute(select(model).order_by(model.departman, getattr(model, alan))))
        .scalars()
        .all()
    )
    return basari(
        [
            GereksinimDTO(id=g.id, departman=g.departman, ad=getattr(g, alan)).model_dump()
            for g in kayitlar
        ],
        mesaj="Gereksinimler",
    )


@router.post(
    "/isg/gereksinimler/{tur}",
    response_model=Zarf[GereksinimDTO],
    status_code=201,
    summary="Gereksinim ekle",
)
async def gereksinim_ekle(tur: str, govde: GereksinimOlusturDTO, k: Yaz, db: Db) -> dict[str, Any]:
    model, alan = _gereksinim_modeli(tur)
    ad = " ".join(govde.ad.split())
    departman = govde.departman.strip()
    var = await db.scalar(
        select(func.count())
        .select_from(model)
        .where(model.departman == departman, getattr(model, alan) == ad)
    )
    if var:
        raise CakismaHatasi("Bu gereksinim zaten tanımlı")
    g = model(departman=departman, **{alan: ad})
    db.add(g)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak=f"{tur}_gereksinimi", kaynak_id=str(g.id), kullanici=k
    )
    return basari(
        GereksinimDTO(id=g.id, departman=g.departman, ad=ad).model_dump(), mesaj="Eklendi"
    )


@router.delete(
    "/isg/gereksinimler/{tur}/{gereksinim_id}",
    response_model=Zarf[None],
    summary="Gereksinim kaldır",
)
async def gereksinim_sil(tur: str, gereksinim_id: int, k: Yaz, db: Db) -> dict[str, Any]:
    model, _alan = _gereksinim_modeli(tur)
    g = await db.get(model, gereksinim_id)
    if g is None:
        raise KaynakBulunamadi("Gereksinim bulunamadı")
    await db.delete(g)
    await db.flush()
    await denetim_yaz(
        db, eylem="sil", kaynak=f"{tur}_gereksinimi", kaynak_id=str(gereksinim_id), kullanici=k
    )
    return basari(None, mesaj="Kaldırıldı")


@router.get("/isg/kkd-eksikleri", response_model=Zarf[list[KkdEksikDTO]], summary="KKD eksikleri")
async def kkd_eksikleri(_k: Oku, db: Db, departman: str | None = None) -> dict[str, Any]:
    return basari(await servis.kkd_eksikleri(db, departman=departman), mesaj="KKD eksikleri")


# ── Tatbikatlar ──────────────────────────────────────────────────────────────


@router.get("/isg/tatbikatlar", response_model=Zarf[list[TatbikatDTO]], summary="Tatbikatlar")
async def tatbikatlar(_k: Oku, db: Db) -> dict[str, Any]:
    kayitlar = (
        (
            await db.execute(
                select(AcilDurumTatbikati)
                .order_by(AcilDurumTatbikati.tarih.desc(), AcilDurumTatbikati.id.desc())
                .limit(500)
            )
        )
        .scalars()
        .all()
    )
    return basari([_tatbikat_cevap(t) for t in kayitlar], mesaj="Tatbikatlar")


@router.post(
    "/isg/tatbikatlar", response_model=Zarf[TatbikatDTO], status_code=201, summary="Tatbikat kaydı"
)
async def tatbikat_olustur(govde: TatbikatOlusturDTO, k: Yaz, db: Db) -> dict[str, Any]:
    if govde.tur not in servis.TATBIKAT_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz tatbikat türü",
            detaylar=[{"alan": "tur", "mesaj": ", ".join(sorted(servis.TATBIKAT_TURLERI))}],
        )
    if govde.sonraki_tarih is not None and govde.sonraki_tarih <= govde.tarih:
        raise DogrulamaHatasi(
            "Sonraki tatbikat tarihi bu tatbikattan sonra olmalı",
            detaylar=[{"alan": "sonraki_tarih", "mesaj": "> tarih"}],
        )
    t = AcilDurumTatbikati(
        kod=f"GECICI-{uuid.uuid4().hex}",
        yurutucu_kullanici_id=k.id,
        **govde.model_dump(),
    )
    db.add(t)
    await db.flush()
    t.kod = servis.yillik_kod("TAT", t.id)
    await db.flush()
    await denetim_yaz(db, eylem="olustur", kaynak="tatbikat", kaynak_id=str(t.id), kullanici=k)
    return basari(_tatbikat_cevap(t), mesaj="Tatbikat kaydedildi")


@router.patch(
    "/isg/tatbikatlar/{tatbikat_id}", response_model=Zarf[TatbikatDTO], summary="Tatbikat düzenle"
)
async def tatbikat_guncelle(
    tatbikat_id: int, govde: TatbikatGuncelleDTO, k: Yaz, db: Db
) -> dict[str, Any]:
    t = await db.get(AcilDurumTatbikati, tatbikat_id)
    if t is None:
        raise KaynakBulunamadi("Tatbikat bulunamadı")
    for alan, deger in govde.model_dump(exclude_unset=True).items():
        setattr(t, alan, deger)
    if t.sonraki_tarih is not None and t.sonraki_tarih <= t.tarih:
        raise DogrulamaHatasi(
            "Sonraki tatbikat tarihi bu tatbikattan sonra olmalı",
            detaylar=[{"alan": "sonraki_tarih", "mesaj": "> tarih"}],
        )
    await db.flush()
    await denetim_yaz(db, eylem="guncelle", kaynak="tatbikat", kaynak_id=str(t.id), kullanici=k)
    return basari(_tatbikat_cevap(t), mesaj="Tatbikat güncellendi")


# ── Kaza → CAPA ──────────────────────────────────────────────────────────────


def _capa_cevap(u: Any) -> dict[str, Any]:
    return KazaCapaDTO(uygunsuzluk_id=u.id, kod=u.kod, durum=u.durum, onem=u.onem).model_dump()


@router.get(
    "/is-kazalari/{kaza_id}/capa",
    response_model=Zarf[KazaCapaDTO | None],
    summary="Kazaya bağlı CAPA vakası (yoksa boş)",
)
async def kaza_capa(kaza_id: int, _k: Oku, db: Db) -> dict[str, Any]:
    if await db.get(IsKazasi, kaza_id) is None:
        raise KaynakBulunamadi("Kaza kaydı bulunamadı")
    u = await servis.kaza_capa(db, kaza_id)
    return basari(_capa_cevap(u) if u else None, mesaj="CAPA bağlantısı")


@router.post(
    "/is-kazalari/{kaza_id}/capa",
    response_model=Zarf[KazaCapaDTO],
    status_code=201,
    summary="Kazadan CAPA vakası aç",
    dependencies=[Depends(modul_gerekli("kalite"))],
)
async def kazadan_capa(
    kaza_id: int,
    govde: CapaAcDTO,
    k: Yaz,
    _kalite: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Db,
) -> dict[str, Any]:
    # Kaza satırı kilitlenir: eşzamanlı iki istekten ikincisi mevcut vakayı görüp 409 alır.
    kaza = await db.get(IsKazasi, kaza_id, with_for_update=True)
    if kaza is None:
        raise KaynakBulunamadi("Kaza kaydı bulunamadı")
    u = await servis.kazadan_capa_ac(db, kaza, k, govde.sorumlu_kullanici_id)
    return basari(_capa_cevap(u), mesaj=f"CAPA vakası açıldı: {u.kod}")
