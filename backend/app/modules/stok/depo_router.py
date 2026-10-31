"""S25-A uçları (``/api/v1``): depo, lokasyon, lokasyon bakiyesi, transfer, sayım (ADR-0024).

İzinler: okuma ``stok:oku``; depo/lokasyon/transfer/sayım yazma ``stok:yaz``; sayım farkının
onayı ``stok:duzeltme`` + sayımı açandan farklı kullanıcı (görev ayrımı). Her yazma denetime
düşer; transfer ve sayım gerçek zamanlı ``stok.hareket`` yayını yapar.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, modul_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.responses import basari
from app.kimlik.models import Kullanici
from app.modules.stok import depo_service, repository
from app.modules.stok.etiket import etiket_pdf
from app.modules.stok.models import (
    Depo,
    Lokasyon,
    Malzeme,
    SayimOturumu,
    SayimSatiri,
    StokBakiyesi,
    StokHareketi,
)

router = APIRouter(tags=["Depo & Sayım"], dependencies=[Depends(modul_gerekli("stok"))])

Oku = Annotated[Kullanici, Depends(izin_gerekli("stok:oku"))]
Yaz = Annotated[Kullanici, Depends(izin_gerekli("stok:yaz"))]
Duzelt = Annotated[Kullanici, Depends(izin_gerekli("stok:duzeltme"))]
Oturum = Annotated[AsyncSession, Depends(get_session)]
TenantDep = Annotated[Tenant, Depends(tenant_cozumle)]


class DepoOlusturDTO(BaseModel):
    kod: str = Field(min_length=1, max_length=30)
    ad: str = Field(min_length=1, max_length=120)
    adres: str = Field(default="", max_length=300)


class LokasyonOlusturDTO(BaseModel):
    depo_id: int
    kod: str = Field(min_length=1, max_length=40)
    ad: str = Field(min_length=1, max_length=120)
    ust_lokasyon_id: int | None = None


class TransferDTO(BaseModel):
    malzeme_id: int
    kaynak_lokasyon_id: int
    hedef_lokasyon_id: int
    miktar: Decimal = Field(gt=0)
    lot_no: str = Field(default="", max_length=60)
    aciklama: str = Field(default="", max_length=500)


class SayimOlusturDTO(BaseModel):
    lokasyon_id: int
    aciklama: str = Field(default="", max_length=500)


class SayimSatirDTO(BaseModel):
    malzeme_id: int
    sayilan_miktar: Decimal = Field(ge=0)
    lot_no: str = Field(default="", max_length=60)


def _depo(d: Depo) -> dict[str, Any]:
    return {"id": d.id, "kod": d.kod, "ad": d.ad, "adres": d.adres, "aktif": d.aktif}


def _lokasyon(lok: Lokasyon) -> dict[str, Any]:
    return {
        "id": lok.id,
        "depo_id": lok.depo_id,
        "ust_lokasyon_id": lok.ust_lokasyon_id,
        "kod": lok.kod,
        "ad": lok.ad,
        "aktif": lok.aktif,
    }


def _hareket(h: StokHareketi) -> dict[str, Any]:
    return {
        "id": h.id,
        "malzeme_id": h.malzeme_id,
        "tur": h.tur,
        "miktar": float(h.miktar),
        "lokasyon_id": h.lokasyon_id,
        "lot_no": h.lot_no,
        "transfer_grubu": h.transfer_grubu,
        "olusturma_tarihi": h.olusturma_tarihi.isoformat() if h.olusturma_tarihi else None,
    }


def _satir(s: SayimSatiri, malzeme: Malzeme | None) -> dict[str, Any]:
    return {
        "id": s.id,
        "malzeme_id": s.malzeme_id,
        "malzeme_kod": malzeme.kod if malzeme else None,
        "malzeme_ad": malzeme.ad if malzeme else None,
        "birim": malzeme.birim if malzeme else None,
        "lot_no": s.lot_no,
        "sistem_miktari": float(s.sistem_miktari),
        "sayilan_miktar": float(s.sayilan_miktar),
        "fark": float(s.fark),
        "uygulanan_hareket_id": s.uygulanan_hareket_id,
    }


async def _sayim_detay(db: AsyncSession, oturum: SayimOturumu) -> dict[str, Any]:
    satirlar = list(
        (
            await db.execute(
                select(SayimSatiri)
                .where(SayimSatiri.oturum_id == oturum.id)
                .order_by(SayimSatiri.id)
            )
        ).scalars()
    )
    malzemeler = {
        m.id: m
        for m in (
            await db.execute(
                select(Malzeme).where(Malzeme.id.in_([s.malzeme_id for s in satirlar] or [0]))
            )
        ).scalars()
    }
    lok = await db.get(Lokasyon, oturum.lokasyon_id)
    return {
        "id": oturum.id,
        "kod": oturum.kod,
        "lokasyon_id": oturum.lokasyon_id,
        "lokasyon_kod": lok.kod if lok else None,
        "durum": oturum.durum,
        "aciklama": oturum.aciklama,
        "olusturan_kullanici_id": oturum.olusturan_kullanici_id,
        "onaylayan_kullanici_id": oturum.onaylayan_kullanici_id,
        "onay_tarihi": oturum.onay_tarihi.isoformat() if oturum.onay_tarihi else None,
        "olusturma_tarihi": oturum.olusturma_tarihi.isoformat()
        if oturum.olusturma_tarihi
        else None,
        "satirlar": [_satir(s, malzemeler.get(s.malzeme_id)) for s in satirlar],
        "fark_sayisi": sum(1 for s in satirlar if s.fark != 0),
    }


async def _sayim_kilitli(db: AsyncSession, sayim_id: int) -> SayimOturumu:
    oturum = (
        await db.execute(select(SayimOturumu).where(SayimOturumu.id == sayim_id).with_for_update())
    ).scalar_one_or_none()
    if oturum is None:
        raise KaynakBulunamadi("Sayım bulunamadı")
    return oturum


# ── Depo & lokasyon ──────────────────────────────────────────────────────────


@router.get("/depolar", summary="Depolar ve lokasyonları (ağaç)")
async def depolar(_k: Oku, db: Oturum) -> dict[str, Any]:
    depo_list = list((await db.execute(select(Depo).order_by(Depo.kod))).scalars())
    loklar = list((await db.execute(select(Lokasyon).order_by(Lokasyon.kod))).scalars())
    toplamlar = dict(
        (
            await db.execute(
                select(StokBakiyesi.lokasyon_id, func.count())
                .where(StokBakiyesi.miktar > 0)
                .group_by(StokBakiyesi.lokasyon_id)
            )
        ).all()
    )
    return basari(
        [
            {
                **_depo(d),
                "lokasyonlar": [
                    {**_lokasyon(lok), "dolu_kalem_sayisi": int(toplamlar.get(lok.id, 0))}
                    for lok in loklar
                    if lok.depo_id == d.id
                ],
            }
            for d in depo_list
        ]
    )


@router.post("/depolar", status_code=201, summary="Depo oluştur")
async def depo_olustur(govde: DepoOlusturDTO, kullanici: Yaz, db: Oturum) -> dict[str, Any]:
    if (await db.execute(select(Depo.id).where(Depo.kod == govde.kod))).scalar_one_or_none():
        raise CakismaHatasi("Bu kodla bir depo zaten var")
    depo = Depo(kod=govde.kod, ad=govde.ad, adres=govde.adres)
    db.add(depo)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="olustur",
        kaynak="depo",
        kaynak_id=str(depo.id),
        kullanici=kullanici,
        detay={"kod": depo.kod},
    )
    return basari(_depo(depo), mesaj="Depo oluşturuldu")


@router.post("/lokasyonlar", status_code=201, summary="Lokasyon oluştur")
async def lokasyon_olustur(govde: LokasyonOlusturDTO, kullanici: Yaz, db: Oturum) -> dict[str, Any]:
    if await db.get(Depo, govde.depo_id) is None:
        raise KaynakBulunamadi("Depo bulunamadı")
    if govde.ust_lokasyon_id is not None:
        ust = await db.get(Lokasyon, govde.ust_lokasyon_id)
        if ust is None or ust.depo_id != govde.depo_id:
            raise DogrulamaHatasi("Üst lokasyon aynı depoda olmalı")
    mevcut = await db.execute(
        select(Lokasyon.id).where(Lokasyon.depo_id == govde.depo_id, Lokasyon.kod == govde.kod)
    )
    if mevcut.scalar_one_or_none():
        raise CakismaHatasi("Bu depoda bu kodla bir lokasyon zaten var")
    lok = Lokasyon(
        depo_id=govde.depo_id, kod=govde.kod, ad=govde.ad, ust_lokasyon_id=govde.ust_lokasyon_id
    )
    db.add(lok)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="olustur",
        kaynak="lokasyon",
        kaynak_id=str(lok.id),
        kullanici=kullanici,
        detay={"depo_id": lok.depo_id, "kod": lok.kod},
    )
    return basari(_lokasyon(lok), mesaj="Lokasyon oluşturuldu")


@router.get("/stok-bakiyeleri", summary="Lokasyon × lot bakiyeleri")
async def bakiyeler(
    _k: Oku, db: Oturum, malzeme_id: int | None = None, lokasyon_id: int | None = None
) -> dict[str, Any]:
    q = (
        select(StokBakiyesi, Malzeme, Lokasyon, Depo)
        .join(Malzeme, Malzeme.id == StokBakiyesi.malzeme_id)
        .join(Lokasyon, Lokasyon.id == StokBakiyesi.lokasyon_id)
        .join(Depo, Depo.id == Lokasyon.depo_id)
        .where(StokBakiyesi.miktar != 0)
        .order_by(Depo.kod, Lokasyon.kod, Malzeme.kod, StokBakiyesi.lot_no)
    )
    if malzeme_id is not None:
        q = q.where(StokBakiyesi.malzeme_id == malzeme_id)
    if lokasyon_id is not None:
        q = q.where(StokBakiyesi.lokasyon_id == lokasyon_id)
    rows = (await db.execute(q)).all()
    return basari(
        [
            {
                "malzeme_id": m.id,
                "malzeme_kod": m.kod,
                "malzeme_ad": m.ad,
                "birim": m.birim,
                "depo_id": d.id,
                "depo_kod": d.kod,
                "lokasyon_id": lok.id,
                "lokasyon_kod": lok.kod,
                "lot_no": b.lot_no,
                "miktar": float(b.miktar),
            }
            for b, m, lok, d in rows
        ]
    )


# ── Transfer ─────────────────────────────────────────────────────────────────


@router.post("/stok-transferleri", status_code=201, summary="Lokasyonlar arası transfer")
async def transfer(
    govde: TransferDTO,
    kullanici: Yaz,
    db: Oturum,
    tenant: TenantDep,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> dict[str, Any]:
    if idempotency_key is not None:
        mevcut = await repository.hareket_idempotent_getir(db, idempotency_key)
        if mevcut is not None:
            ikiz = (
                await db.execute(
                    select(StokHareketi).where(
                        StokHareketi.transfer_grubu == mevcut.transfer_grubu,
                        StokHareketi.id != mevcut.id,
                    )
                )
            ).scalar_one_or_none()
            return basari(
                {"cikis": _hareket(mevcut), "giris": _hareket(ikiz) if ikiz else None},
                mesaj="Transfer zaten işlenmiş",
            )
    malzeme = await repository.malzeme_getir_kilitli(db, govde.malzeme_id)
    if malzeme is None:
        raise KaynakBulunamadi("Malzeme bulunamadı")
    cikis, giris = await depo_service.transfer_uygula(
        db,
        malzeme,
        kaynak_lokasyon_id=govde.kaynak_lokasyon_id,
        hedef_lokasyon_id=govde.hedef_lokasyon_id,
        miktar=govde.miktar,
        lot_no=govde.lot_no,
        aciklama=govde.aciklama,
        kullanici=kullanici,
        idempotency_anahtari=idempotency_key,
    )
    await denetim_yaz(
        db,
        eylem="transfer",
        kaynak="stok_hareketi",
        kaynak_id=str(cikis.id),
        kullanici=kullanici,
        detay={
            "malzeme_id": malzeme.id,
            "miktar": str(govde.miktar),
            "kaynak": govde.kaynak_lokasyon_id,
            "hedef": govde.hedef_lokasyon_id,
            "grup": cikis.transfer_grubu,
        },
    )
    await yayinla(tenant.slug, {"tur": "stok.hareket", "malzeme_id": malzeme.id})
    return basari({"cikis": _hareket(cikis), "giris": _hareket(giris)}, mesaj="Transfer yapıldı")


# ── Sayım ────────────────────────────────────────────────────────────────────


@router.get("/sayimlar", summary="Sayım oturumları")
async def sayimlar(_k: Oku, db: Oturum, durum: str | None = None) -> dict[str, Any]:
    q = select(SayimOturumu).order_by(SayimOturumu.id.desc()).limit(200)
    if durum:
        q = q.where(SayimOturumu.durum == durum)
    rows = list((await db.execute(q)).scalars())
    return basari([await _sayim_detay(db, o) for o in rows])


@router.post("/sayimlar", status_code=201, summary="Sayım aç (lokasyon)")
async def sayim_ac(govde: SayimOlusturDTO, kullanici: Yaz, db: Oturum) -> dict[str, Any]:
    await depo_service.lokasyon_getir(db, govde.lokasyon_id)
    oturum = SayimOturumu(
        kod=depo_service.sayim_gecici_kod(),
        lokasyon_id=govde.lokasyon_id,
        aciklama=govde.aciklama,
        olusturan_kullanici_id=kullanici.id,
    )
    db.add(oturum)
    await db.flush()
    oturum.kod = depo_service.sayim_kalici_kod(oturum.id)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="olustur",
        kaynak="sayim",
        kaynak_id=str(oturum.id),
        kullanici=kullanici,
        detay={"lokasyon_id": govde.lokasyon_id},
    )
    return basari(await _sayim_detay(db, oturum), mesaj="Sayım açıldı")


@router.get("/sayimlar/{sayim_id}", summary="Sayım detayı")
async def sayim_detay(sayim_id: int, _k: Oku, db: Oturum) -> dict[str, Any]:
    oturum = await db.get(SayimOturumu, sayim_id)
    if oturum is None:
        raise KaynakBulunamadi("Sayım bulunamadı")
    return basari(await _sayim_detay(db, oturum))


@router.put("/sayimlar/{sayim_id}/satirlar", summary="Sayım satırı yaz (malzeme başına)")
async def sayim_satir(sayim_id: int, govde: SayimSatirDTO, _k: Yaz, db: Oturum) -> dict[str, Any]:
    oturum = await _sayim_kilitli(db, sayim_id)
    malzeme = await db.get(Malzeme, govde.malzeme_id)
    if malzeme is None:
        raise KaynakBulunamadi("Malzeme bulunamadı")
    await depo_service.sayim_satiri_yaz(
        db, oturum, malzeme, lot_no=govde.lot_no, sayilan_miktar=govde.sayilan_miktar
    )
    return basari(await _sayim_detay(db, oturum), mesaj="Satır kaydedildi")


@router.post("/sayimlar/{sayim_id}/gonder", summary="Sayımı onaya gönder")
async def sayim_gonder(sayim_id: int, kullanici: Yaz, db: Oturum) -> dict[str, Any]:
    oturum = await _sayim_kilitli(db, sayim_id)
    depo_service.sayim_gecisi(oturum, "onay_bekliyor")
    await denetim_yaz(
        db, eylem="gonder", kaynak="sayim", kaynak_id=str(oturum.id), kullanici=kullanici, detay={}
    )
    return basari(await _sayim_detay(db, oturum), mesaj="Sayım onaya gönderildi")


@router.post("/sayimlar/{sayim_id}/onayla", summary="Sayım farklarını uygula (delta)")
async def sayim_onay(
    sayim_id: int, kullanici: Duzelt, db: Oturum, tenant: TenantDep
) -> dict[str, Any]:
    oturum = await _sayim_kilitli(db, sayim_id)
    hareketler = await depo_service.sayim_onayla(db, oturum, onaylayan=kullanici)
    await denetim_yaz(
        db,
        eylem="onayla",
        kaynak="sayim",
        kaynak_id=str(oturum.id),
        kullanici=kullanici,
        detay={"uygulanan_hareket": [h.id for h in hareketler]},
    )
    for h in hareketler:
        await yayinla(tenant.slug, {"tur": "stok.hareket", "malzeme_id": h.malzeme_id})
    return basari(await _sayim_detay(db, oturum), mesaj=f"{len(hareketler)} fark uygulandı")


@router.post("/sayimlar/{sayim_id}/iptal", summary="Sayımı iptal et")
async def sayim_iptal(sayim_id: int, kullanici: Yaz, db: Oturum) -> dict[str, Any]:
    oturum = await _sayim_kilitli(db, sayim_id)
    depo_service.sayim_gecisi(oturum, "iptal")
    await denetim_yaz(
        db, eylem="iptal", kaynak="sayim", kaynak_id=str(oturum.id), kullanici=kullanici, detay={}
    )
    return basari(await _sayim_detay(db, oturum), mesaj="Sayım iptal edildi")


# ── Etiket & kodla bulma (S25-B) ─────────────────────────────────────────────


@router.get("/malzemeler/{malzeme_id}/etiket.pdf", summary="Malzeme etiketi (QR + Code 128)")
async def malzeme_etiketi(
    malzeme_id: int, _k: Oku, db: Oturum, adet: Annotated[int, Query(ge=1, le=100)] = 1
) -> Response:
    malzeme = await db.get(Malzeme, malzeme_id)
    if malzeme is None:
        raise KaynakBulunamadi("Malzeme bulunamadı")
    return Response(
        content=etiket_pdf(malzeme, adet),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="etiket-{malzeme.id}.pdf"'},
    )


@router.get("/malzeme-kodu", summary="Okutulan koddan malzemeyi bul (tam eşleşme)")
async def malzeme_kodla(
    _k: Oku, db: Oturum, kod: Annotated[str, Query(min_length=1, max_length=50)]
) -> dict[str, Any]:
    malzeme = (
        await db.execute(select(Malzeme).where(Malzeme.kod == kod.strip()))
    ).scalar_one_or_none()
    if malzeme is None:
        raise KaynakBulunamadi("Bu kodla malzeme yok")
    return basari({"id": malzeme.id, "kod": malzeme.kod, "ad": malzeme.ad})
