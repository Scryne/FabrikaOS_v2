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
from app.modules.stok.models import (
    Malzeme,
    SatinalmaTalebi,
    SatinalmaTalebiKalemi,
    StokHareketi,
)
from app.modules.stok.schemas import (
    MalzemeCevapDTO,
    MalzemeGuncelleDTO,
    MalzemeOlusturDTO,
    RedDTO,
    SatinalmaKalemCevapDTO,
    SatinalmaKalemDTO,
    SatinalmaTalebiCevapDTO,
    SatinalmaTalebiDetayDTO,
    SatinalmaTalebiGuncelleDTO,
    SatinalmaTalebiOlusturDTO,
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


# --- Satınalma talebi ---
def _tahmini_toplam(kalemler: list[SatinalmaTalebiKalemi]) -> float | None:
    parcalar = [
        k.miktar * k.tahmini_birim_fiyat for k in kalemler if k.tahmini_birim_fiyat is not None
    ]
    return float(sum(parcalar)) if parcalar else None


def _talep_cevap(t: SatinalmaTalebi) -> dict[str, Any]:
    return SatinalmaTalebiCevapDTO(
        id=t.id,
        kod=t.kod,
        baslik=t.baslik,
        aciklama=t.aciklama,
        durum=t.durum,
        para_birimi=t.para_birimi,
        talep_eden_kullanici_id=t.talep_eden_kullanici_id,
        onaylayan_kullanici_id=t.onaylayan_kullanici_id,
        onay_tarihi=t.onay_tarihi,
        red_nedeni=t.red_nedeni,
        olusturma_tarihi=t.olusturma_tarihi,
    ).model_dump()


def _talep_detay_cevap(t: SatinalmaTalebi) -> dict[str, Any]:
    return SatinalmaTalebiDetayDTO(
        id=t.id,
        kod=t.kod,
        baslik=t.baslik,
        aciklama=t.aciklama,
        durum=t.durum,
        para_birimi=t.para_birimi,
        talep_eden_kullanici_id=t.talep_eden_kullanici_id,
        onaylayan_kullanici_id=t.onaylayan_kullanici_id,
        onay_tarihi=t.onay_tarihi,
        red_nedeni=t.red_nedeni,
        tahmini_toplam=_tahmini_toplam(list(t.kalemler)),
        olusturma_tarihi=t.olusturma_tarihi,
        kalemler=[
            SatinalmaKalemCevapDTO(
                id=k.id,
                malzeme_id=k.malzeme_id,
                miktar=float(k.miktar),
                birim=k.birim,
                tahmini_birim_fiyat=(
                    float(k.tahmini_birim_fiyat) if k.tahmini_birim_fiyat is not None else None
                ),
                aciklama=k.aciklama,
            )
            for k in t.kalemler
        ],
    ).model_dump()


async def _kalemleri_dogrula(db: AsyncSession, kalemler: list[SatinalmaKalemDTO]) -> None:
    for k in kalemler:
        if k.birim not in BIRIMLER:
            raise DogrulamaHatasi(
                "Geçersiz birim",
                detaylar=[
                    {"alan": "kalemler.birim", "mesaj": f"Geçerli: {', '.join(sorted(BIRIMLER))}"}
                ],
            )
        if await repository.malzeme_getir(db, k.malzeme_id) is None:
            raise KaynakBulunamadi(f"Malzeme bulunamadı: {k.malzeme_id}")


@router.post(
    "/satinalma-talepleri",
    response_model=Zarf[SatinalmaTalebiDetayDTO],
    status_code=201,
    summary="Satınalma talebi oluştur (çok-kalemli)",
)
async def talep_olustur(
    govde: SatinalmaTalebiOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    await _kalemleri_dogrula(db, govde.kalemler)
    talep = SatinalmaTalebi(
        kod=service.talep_gecici_kod(),
        baslik=govde.baslik,
        aciklama=govde.aciklama,
        para_birimi=govde.para_birimi,
        talep_eden_kullanici_id=kullanici.id,
        kalemler=[
            SatinalmaTalebiKalemi(
                malzeme_id=k.malzeme_id,
                miktar=k.miktar,
                birim=k.birim,
                tahmini_birim_fiyat=k.tahmini_birim_fiyat,
                aciklama=k.aciklama,
            )
            for k in govde.kalemler
        ],
    )
    await repository.talep_ekle(db, talep)
    talep.kod = service.talep_kalici_kod(talep.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="satinalma_talebi", kaynak_id=str(talep.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "satinalma.durum", "id": talep.id, "durum": talep.durum})
    talep_tam = await repository.talep_getir_kalemli(db, talep.id)
    assert talep_tam is not None
    return basari(_talep_detay_cevap(talep_tam), mesaj="Satınalma talebi oluşturuldu")


@router.get(
    "/satinalma-talepleri",
    response_model=Zarf[list[SatinalmaTalebiCevapDTO]],
    summary="Satınalma taleplerini listele",
)
async def talep_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    durum: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.talep_listele(
        db, sayfa=sayfa, adet=adet, durum=durum, arama=arama, siralama=siralama, yon=yon
    )
    return sayfali([_talep_cevap(t) for t in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/satinalma-talepleri/{talep_id}",
    response_model=Zarf[SatinalmaTalebiDetayDTO],
    summary="Satınalma talebi detayı (kalemlerle)",
)
async def talep_detay(
    talep_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    talep = await repository.talep_getir_kalemli(db, talep_id)
    if talep is None:
        raise KaynakBulunamadi("Satınalma talebi bulunamadı")
    return basari(_talep_detay_cevap(talep), mesaj="Satınalma talebi detayı")


@router.patch(
    "/satinalma-talepleri/{talep_id}",
    response_model=Zarf[SatinalmaTalebiDetayDTO],
    summary="Satınalma talebini düzenle (yalnız taslak)",
)
async def talep_guncelle(
    talep_id: int,
    govde: SatinalmaTalebiGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    talep = await repository.talep_getir_kalemli(db, talep_id)
    if talep is None:
        raise KaynakBulunamadi("Satınalma talebi bulunamadı")
    if talep.durum != "taslak":
        raise CakismaHatasi("Yalnız taslak talep düzenlenebilir")
    if govde.baslik is not None:
        talep.baslik = govde.baslik
    if govde.aciklama is not None:
        talep.aciklama = govde.aciklama
    if govde.para_birimi is not None:
        talep.para_birimi = govde.para_birimi
    if govde.kalemler is not None:
        await _kalemleri_dogrula(db, govde.kalemler)
        talep.kalemler = [
            SatinalmaTalebiKalemi(
                malzeme_id=k.malzeme_id,
                miktar=k.miktar,
                birim=k.birim,
                tahmini_birim_fiyat=k.tahmini_birim_fiyat,
                aciklama=k.aciklama,
            )
            for k in govde.kalemler
        ]
    await db.flush()
    await denetim_yaz(
        db,
        eylem="guncelle",
        kaynak="satinalma_talebi",
        kaynak_id=str(talep.id),
        kullanici=kullanici,
    )
    talep_tam = await repository.talep_getir_kalemli(db, talep.id)
    assert talep_tam is not None
    return basari(_talep_detay_cevap(talep_tam), mesaj="Satınalma talebi güncellendi")


async def _gecis(
    db: AsyncSession,
    tenant: Tenant,
    kullanici: Kullanici,
    talep_id: int,
    hedef: str,
    *,
    onaylayan: Kullanici | None = None,
    red_nedeni: str | None = None,
) -> dict[str, Any]:
    talep = await repository.talep_getir_kilitli(db, talep_id)
    if talep is None:
        raise KaynakBulunamadi("Satınalma talebi bulunamadı")
    await service.talep_durum_gecisi(
        db, talep, hedef=hedef, onaylayan=onaylayan, red_nedeni=red_nedeni
    )
    await denetim_yaz(
        db,
        eylem="durum_guncelle",
        kaynak="satinalma_talebi",
        kaynak_id=str(talep.id),
        kullanici=kullanici,
        detay={"durum": talep.durum},
    )
    await yayinla(tenant.slug, {"tur": "satinalma.durum", "id": talep.id, "durum": talep.durum})
    return basari(_talep_cevap(talep), mesaj="Durum güncellendi")


@router.post(
    "/satinalma-talepleri/{talep_id}/gonder",
    response_model=Zarf[SatinalmaTalebiCevapDTO],
    summary="Talebi onaya gönder",
)
async def talep_gonder(
    talep_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _gecis(db, tenant, kullanici, talep_id, "onay_bekliyor")


@router.post(
    "/satinalma-talepleri/{talep_id}/onayla",
    response_model=Zarf[SatinalmaTalebiCevapDTO],
    summary="Talebi onayla",
)
async def talep_onayla(
    talep_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:onay"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _gecis(db, tenant, kullanici, talep_id, "onaylandi", onaylayan=kullanici)


@router.post(
    "/satinalma-talepleri/{talep_id}/reddet",
    response_model=Zarf[SatinalmaTalebiCevapDTO],
    summary="Talebi reddet",
)
async def talep_reddet(
    talep_id: int,
    govde: RedDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:onay"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _gecis(
        db,
        tenant,
        kullanici,
        talep_id,
        "reddedildi",
        onaylayan=kullanici,
        red_nedeni=govde.red_nedeni,
    )


@router.post(
    "/satinalma-talepleri/{talep_id}/iptal",
    response_model=Zarf[SatinalmaTalebiCevapDTO],
    summary="Talebi iptal et",
)
async def talep_iptal(
    talep_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("satinalma:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _gecis(db, tenant, kullanici, talep_id, "iptal")
