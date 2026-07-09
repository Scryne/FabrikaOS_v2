"""İK uçları (``/api/v1``) — personel + izin talebi + fazla mesai + zimmet + sertifika.

Tüm uçlar tenant-kapsamlı + RBAC. Personel/izin/mesai/zimmet/sertifika okuma ``ik:oku``,
yazma ``ik:yaz`` ister; izin talebi **onay/red** ayrıca ``ik:onay`` ister (görev ayrımı).
KVKK: personel yanıtlarında TC kimlik ``tc_maskele`` ile maskelenir.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.ik import repository, service
from app.modules.ik.birimler import IZIN_TURLERI
from app.modules.ik.models import FazlaMesai, IzinTalebi, Personel, Sertifika, Zimmet
from app.modules.ik.schemas import (
    FazlaMesaiCevapDTO,
    FazlaMesaiOlusturDTO,
    IkOzetDTO,
    IzinTalebiCevapDTO,
    IzinTalebiGuncelleDTO,
    IzinTalebiOlusturDTO,
    PersonelCevapDTO,
    PersonelGuncelleDTO,
    PersonelOlusturDTO,
    RedDTO,
    SertifikaCevapDTO,
    SertifikaOlusturDTO,
    ZimmetCevapDTO,
    ZimmetOlusturDTO,
)

router = APIRouter(tags=["İK"])


# --- Personel (KVKK: TC maskeli) ---
def _personel_cevap(p: Personel) -> dict[str, Any]:
    return PersonelCevapDTO(
        id=p.id,
        sicil_no=p.sicil_no,
        ad=p.ad,
        soyad=p.soyad,
        tc_kimlik_no=service.tc_maskele(p.tc_kimlik_no),
        dogum_tarihi=p.dogum_tarihi,
        telefon=p.telefon,
        eposta=p.eposta,
        departman=p.departman,
        unvan=p.unvan,
        ise_giris_tarihi=p.ise_giris_tarihi,
        yillik_izin_hakki=p.yillik_izin_hakki,
        kullanici_id=p.kullanici_id,
        aktif=p.aktif,
        olusturma_tarihi=p.olusturma_tarihi,
    ).model_dump()


@router.post(
    "/personeller",
    response_model=Zarf[PersonelCevapDTO],
    status_code=201,
    summary="Personel oluştur",
)
async def personel_olustur(
    govde: PersonelOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if await repository.personel_sicil_ile(db, govde.sicil_no) is not None:
        raise CakismaHatasi(f"Sicil no zaten kayıtlı: {govde.sicil_no}")
    personel = Personel(
        sicil_no=govde.sicil_no,
        ad=govde.ad,
        soyad=govde.soyad,
        tc_kimlik_no=govde.tc_kimlik_no,
        dogum_tarihi=govde.dogum_tarihi,
        telefon=govde.telefon,
        eposta=govde.eposta,
        departman=govde.departman,
        unvan=govde.unvan,
        ise_giris_tarihi=govde.ise_giris_tarihi,
        yillik_izin_hakki=govde.yillik_izin_hakki,
        kullanici_id=govde.kullanici_id,
        aktif=govde.aktif,
    )
    await repository.personel_ekle(db, personel)
    await denetim_yaz(
        db, eylem="olustur", kaynak="personel", kaynak_id=str(personel.id), kullanici=kullanici
    )
    return basari(_personel_cevap(personel), mesaj="Personel oluşturuldu")


@router.get(
    "/personeller",
    response_model=Zarf[list[PersonelCevapDTO]],
    summary="Personelleri listele",
)
async def personel_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    departman: str | None = None,
    aktif: bool | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.personel_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        departman=departman,
        aktif=aktif,
        arama=arama,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_personel_cevap(p) for p in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/personeller/{personel_id}",
    response_model=Zarf[PersonelCevapDTO],
    summary="Personel detayı",
)
async def personel_detay(
    personel_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    personel = await repository.personel_getir(db, personel_id)
    if personel is None:
        raise KaynakBulunamadi("Personel bulunamadı")
    return basari(_personel_cevap(personel), mesaj="Personel detayı")


@router.patch(
    "/personeller/{personel_id}",
    response_model=Zarf[PersonelCevapDTO],
    summary="Personel düzenle",
)
async def personel_guncelle(
    personel_id: int,
    govde: PersonelGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    personel = await repository.personel_getir(db, personel_id)
    if personel is None:
        raise KaynakBulunamadi("Personel bulunamadı")
    for alan in (
        "ad",
        "soyad",
        "tc_kimlik_no",
        "dogum_tarihi",
        "telefon",
        "eposta",
        "departman",
        "unvan",
        "ise_giris_tarihi",
        "yillik_izin_hakki",
        "kullanici_id",
        "aktif",
    ):
        deger = getattr(govde, alan)
        if deger is not None:
            setattr(personel, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="personel", kaynak_id=str(personel.id), kullanici=kullanici
    )
    return basari(_personel_cevap(personel), mesaj="Personel güncellendi")


# --- İzin talebi (onay akışı: gönder → onayla/reddet; onay ik:onay ister) ---
def _izin_cevap(i: IzinTalebi) -> dict[str, Any]:
    return IzinTalebiCevapDTO(
        id=i.id,
        kod=i.kod,
        personel_id=i.personel_id,
        izin_turu=i.izin_turu,
        baslangic_tarihi=i.baslangic_tarihi,
        bitis_tarihi=i.bitis_tarihi,
        gun_sayisi=i.gun_sayisi,
        aciklama=i.aciklama,
        durum=i.durum,
        talep_eden_kullanici_id=i.talep_eden_kullanici_id,
        onaylayan_kullanici_id=i.onaylayan_kullanici_id,
        onay_tarihi=i.onay_tarihi,
        red_nedeni=i.red_nedeni,
        olusturma_tarihi=i.olusturma_tarihi,
    ).model_dump()


@router.post(
    "/izin-talepleri",
    response_model=Zarf[IzinTalebiCevapDTO],
    status_code=201,
    summary="İzin talebi oluştur",
)
async def izin_olustur(
    govde: IzinTalebiOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    if govde.izin_turu not in IZIN_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz izin türü",
            detaylar=[
                {"alan": "izin_turu", "mesaj": f"Geçerli: {', '.join(sorted(IZIN_TURLERI))}"}
            ],
        )
    if govde.bitis_tarihi < govde.baslangic_tarihi:
        raise DogrulamaHatasi(
            "Bitiş tarihi başlangıçtan önce olamaz",
            detaylar=[{"alan": "bitis_tarihi", "mesaj": ">= baslangic_tarihi"}],
        )
    if await repository.personel_getir(db, govde.personel_id) is None:
        raise KaynakBulunamadi("Personel bulunamadı")
    izin = IzinTalebi(
        kod=service.izin_gecici_kod(),
        personel_id=govde.personel_id,
        izin_turu=govde.izin_turu,
        baslangic_tarihi=govde.baslangic_tarihi,
        bitis_tarihi=govde.bitis_tarihi,
        gun_sayisi=service.izin_gun_sayisi(govde.baslangic_tarihi, govde.bitis_tarihi),
        aciklama=govde.aciklama,
        talep_eden_kullanici_id=kullanici.id,
    )
    await repository.izin_ekle(db, izin)
    izin.kod = service.izin_kalici_kod(izin.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="izin_talebi", kaynak_id=str(izin.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "ik.izin", "id": izin.id, "durum": izin.durum})
    return basari(_izin_cevap(izin), mesaj="İzin talebi oluşturuldu")


@router.get(
    "/izin-talepleri",
    response_model=Zarf[list[IzinTalebiCevapDTO]],
    summary="İzin taleplerini listele",
)
async def izin_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    personel_id: int | None = None,
    durum: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.izin_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        personel_id=personel_id,
        durum=durum,
        arama=arama,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_izin_cevap(i) for i in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/izin-talepleri/{izin_id}",
    response_model=Zarf[IzinTalebiCevapDTO],
    summary="İzin talebi detayı",
)
async def izin_detay(
    izin_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    izin = await repository.izin_getir(db, izin_id)
    if izin is None:
        raise KaynakBulunamadi("İzin talebi bulunamadı")
    return basari(_izin_cevap(izin), mesaj="İzin talebi detayı")


@router.patch(
    "/izin-talepleri/{izin_id}",
    response_model=Zarf[IzinTalebiCevapDTO],
    summary="İzin talebini düzenle (yalnız taslak)",
)
async def izin_guncelle(
    izin_id: int,
    govde: IzinTalebiGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    izin = await repository.izin_getir(db, izin_id)
    if izin is None:
        raise KaynakBulunamadi("İzin talebi bulunamadı")
    if izin.durum != "taslak":
        raise CakismaHatasi("Yalnız taslak izin talebi düzenlenebilir")
    if govde.izin_turu is not None:
        if govde.izin_turu not in IZIN_TURLERI:
            raise DogrulamaHatasi(
                "Geçersiz izin türü",
                detaylar=[
                    {"alan": "izin_turu", "mesaj": f"Geçerli: {', '.join(sorted(IZIN_TURLERI))}"}
                ],
            )
        izin.izin_turu = govde.izin_turu
    if govde.aciklama is not None:
        izin.aciklama = govde.aciklama
    if govde.baslangic_tarihi is not None:
        izin.baslangic_tarihi = govde.baslangic_tarihi
    if govde.bitis_tarihi is not None:
        izin.bitis_tarihi = govde.bitis_tarihi
    if govde.baslangic_tarihi is not None or govde.bitis_tarihi is not None:
        if izin.bitis_tarihi < izin.baslangic_tarihi:
            raise DogrulamaHatasi(
                "Bitiş tarihi başlangıçtan önce olamaz",
                detaylar=[{"alan": "bitis_tarihi", "mesaj": ">= baslangic_tarihi"}],
            )
        izin.gun_sayisi = service.izin_gun_sayisi(izin.baslangic_tarihi, izin.bitis_tarihi)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="izin_talebi", kaynak_id=str(izin.id), kullanici=kullanici
    )
    return basari(_izin_cevap(izin), mesaj="İzin talebi güncellendi")


async def _izin_gecis(
    db: AsyncSession,
    tenant: Tenant,
    kullanici: Kullanici,
    izin_id: int,
    hedef: str,
    *,
    onaylayan: Kullanici | None = None,
    red_nedeni: str | None = None,
) -> dict[str, Any]:
    izin = await repository.izin_getir_kilitli(db, izin_id)
    if izin is None:
        raise KaynakBulunamadi("İzin talebi bulunamadı")
    await service.izin_durum_gecisi(
        db, izin, hedef=hedef, onaylayan=onaylayan, red_nedeni=red_nedeni
    )
    await denetim_yaz(
        db,
        eylem="durum_guncelle",
        kaynak="izin_talebi",
        kaynak_id=str(izin.id),
        kullanici=kullanici,
        detay={"durum": izin.durum},
    )
    await yayinla(tenant.slug, {"tur": "ik.izin", "id": izin.id, "durum": izin.durum})
    return basari(_izin_cevap(izin), mesaj="Durum güncellendi")


@router.post(
    "/izin-talepleri/{izin_id}/gonder",
    response_model=Zarf[IzinTalebiCevapDTO],
    summary="İzin talebini onaya gönder",
)
async def izin_gonder(
    izin_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _izin_gecis(db, tenant, kullanici, izin_id, "onay_bekliyor")


@router.post(
    "/izin-talepleri/{izin_id}/onayla",
    response_model=Zarf[IzinTalebiCevapDTO],
    summary="İzin talebini onayla (ik:onay)",
)
async def izin_onayla(
    izin_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:onay"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _izin_gecis(db, tenant, kullanici, izin_id, "onaylandi", onaylayan=kullanici)


@router.post(
    "/izin-talepleri/{izin_id}/reddet",
    response_model=Zarf[IzinTalebiCevapDTO],
    summary="İzin talebini reddet (ik:onay)",
)
async def izin_reddet(
    izin_id: int,
    govde: RedDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:onay"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _izin_gecis(
        db,
        tenant,
        kullanici,
        izin_id,
        "reddedildi",
        onaylayan=kullanici,
        red_nedeni=govde.red_nedeni,
    )


@router.post(
    "/izin-talepleri/{izin_id}/iptal",
    response_model=Zarf[IzinTalebiCevapDTO],
    summary="İzin talebini iptal et",
)
async def izin_iptal(
    izin_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    return await _izin_gecis(db, tenant, kullanici, izin_id, "iptal")


async def _personel_zorunlu(db: AsyncSession, personel_id: int) -> None:
    if await repository.personel_getir(db, personel_id) is None:
        raise KaynakBulunamadi("Personel bulunamadı")


# --- Fazla mesai ---
def _mesai_cevap(m: FazlaMesai) -> dict[str, Any]:
    return FazlaMesaiCevapDTO(
        id=m.id,
        personel_id=m.personel_id,
        tarih=m.tarih,
        saat=float(m.saat),
        aciklama=m.aciklama,
        onayli=m.onayli,
        olusturan_kullanici_id=m.olusturan_kullanici_id,
        olusturma_tarihi=m.olusturma_tarihi,
    ).model_dump()


@router.post(
    "/fazla-mesailer",
    response_model=Zarf[FazlaMesaiCevapDTO],
    status_code=201,
    summary="Fazla mesai kaydı oluştur",
)
async def mesai_olustur(
    govde: FazlaMesaiOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    await _personel_zorunlu(db, govde.personel_id)
    mesai = FazlaMesai(
        personel_id=govde.personel_id,
        tarih=govde.tarih,
        saat=govde.saat,
        aciklama=govde.aciklama,
        olusturan_kullanici_id=kullanici.id,
    )
    await repository.mesai_ekle(db, mesai)
    await denetim_yaz(
        db, eylem="olustur", kaynak="fazla_mesai", kaynak_id=str(mesai.id), kullanici=kullanici
    )
    return basari(_mesai_cevap(mesai), mesaj="Fazla mesai kaydı oluşturuldu")


@router.get(
    "/fazla-mesailer",
    response_model=Zarf[list[FazlaMesaiCevapDTO]],
    summary="Fazla mesaileri listele",
)
async def mesai_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    personel_id: int | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.mesai_listele(
        db, sayfa=sayfa, adet=adet, personel_id=personel_id
    )
    return sayfali([_mesai_cevap(m) for m in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.post(
    "/fazla-mesailer/{mesai_id}/onayla",
    response_model=Zarf[FazlaMesaiCevapDTO],
    summary="Fazla mesaiyi onayla",
)
async def mesai_onayla(
    mesai_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:onay"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    mesai = await repository.mesai_getir(db, mesai_id)
    if mesai is None:
        raise KaynakBulunamadi("Fazla mesai bulunamadı")
    mesai.onayli = True
    await db.flush()
    await denetim_yaz(
        db, eylem="onayla", kaynak="fazla_mesai", kaynak_id=str(mesai.id), kullanici=kullanici
    )
    return basari(_mesai_cevap(mesai), mesaj="Fazla mesai onaylandı")


# --- Zimmet ---
def _zimmet_cevap(z: Zimmet) -> dict[str, Any]:
    return ZimmetCevapDTO(
        id=z.id,
        personel_id=z.personel_id,
        demirbas=z.demirbas,
        seri_no=z.seri_no,
        zimmet_tarihi=z.zimmet_tarihi,
        iade_tarihi=z.iade_tarihi,
        durum=z.durum,
        aciklama=z.aciklama,
        olusturma_tarihi=z.olusturma_tarihi,
    ).model_dump()


@router.post(
    "/zimmetler",
    response_model=Zarf[ZimmetCevapDTO],
    status_code=201,
    summary="Zimmet (demirbaş atama) oluştur",
)
async def zimmet_olustur(
    govde: ZimmetOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    await _personel_zorunlu(db, govde.personel_id)
    zimmet = Zimmet(
        personel_id=govde.personel_id,
        demirbas=govde.demirbas,
        seri_no=govde.seri_no,
        zimmet_tarihi=govde.zimmet_tarihi,
        aciklama=govde.aciklama,
    )
    await repository.zimmet_ekle(db, zimmet)
    await denetim_yaz(
        db, eylem="olustur", kaynak="zimmet", kaynak_id=str(zimmet.id), kullanici=kullanici
    )
    return basari(_zimmet_cevap(zimmet), mesaj="Zimmet oluşturuldu")


@router.get(
    "/zimmetler",
    response_model=Zarf[list[ZimmetCevapDTO]],
    summary="Zimmetleri listele",
)
async def zimmet_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    personel_id: int | None = None,
    durum: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.zimmet_listele(
        db, sayfa=sayfa, adet=adet, personel_id=personel_id, durum=durum
    )
    return sayfali([_zimmet_cevap(z) for z in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.post(
    "/zimmetler/{zimmet_id}/iade",
    response_model=Zarf[ZimmetCevapDTO],
    summary="Zimmeti iade al",
)
async def zimmet_iade(
    zimmet_id: int,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    zimmet = await repository.zimmet_getir(db, zimmet_id)
    if zimmet is None:
        raise KaynakBulunamadi("Zimmet bulunamadı")
    if zimmet.durum == "iade_edildi":
        raise CakismaHatasi("Zimmet zaten iade edilmiş")
    zimmet.durum = "iade_edildi"
    zimmet.iade_tarihi = datetime.now(UTC).date()
    await db.flush()
    await denetim_yaz(
        db, eylem="iade", kaynak="zimmet", kaynak_id=str(zimmet.id), kullanici=kullanici
    )
    return basari(_zimmet_cevap(zimmet), mesaj="Zimmet iade alındı")


# --- Sertifika ---
def _sertifika_cevap(s: Sertifika) -> dict[str, Any]:
    return SertifikaCevapDTO(
        id=s.id,
        personel_id=s.personel_id,
        ad=s.ad,
        kurum=s.kurum,
        belge_no=s.belge_no,
        alinma_tarihi=s.alinma_tarihi,
        gecerlilik_tarihi=s.gecerlilik_tarihi,
        aciklama=s.aciklama,
        olusturma_tarihi=s.olusturma_tarihi,
    ).model_dump()


@router.post(
    "/sertifikalar",
    response_model=Zarf[SertifikaCevapDTO],
    status_code=201,
    summary="Sertifika / eğitim kaydı oluştur",
)
async def sertifika_olustur(
    govde: SertifikaOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    await _personel_zorunlu(db, govde.personel_id)
    sertifika = Sertifika(
        personel_id=govde.personel_id,
        ad=govde.ad,
        kurum=govde.kurum,
        belge_no=govde.belge_no,
        alinma_tarihi=govde.alinma_tarihi,
        gecerlilik_tarihi=govde.gecerlilik_tarihi,
        aciklama=govde.aciklama,
    )
    await repository.sertifika_ekle(db, sertifika)
    await denetim_yaz(
        db, eylem="olustur", kaynak="sertifika", kaynak_id=str(sertifika.id), kullanici=kullanici
    )
    return basari(_sertifika_cevap(sertifika), mesaj="Sertifika kaydı oluşturuldu")


@router.get(
    "/sertifikalar",
    response_model=Zarf[list[SertifikaCevapDTO]],
    summary="Sertifikaları listele",
)
async def sertifika_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    personel_id: int | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.sertifika_listele(
        db, sayfa=sayfa, adet=adet, personel_id=personel_id
    )
    return sayfali([_sertifika_cevap(s) for s in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get("/ik/ozet", response_model=Zarf[IkOzetDTO], summary="İK özeti (KPI)")
async def ik_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("ik:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    bugun = datetime.now(UTC).date()
    sinir = bugun + timedelta(days=30)

    toplam = await db.scalar(select(func.count()).select_from(Personel)) or 0
    aktif = (
        await db.scalar(select(func.count()).select_from(Personel).where(Personel.aktif.is_(True)))
        or 0
    )
    bugun_izinli = (
        await db.scalar(
            select(func.count())
            .select_from(IzinTalebi)
            .where(
                IzinTalebi.durum == "onaylandi",
                IzinTalebi.baslangic_tarihi <= bugun,
                IzinTalebi.bitis_tarihi >= bugun,
            )
        )
        or 0
    )
    yaklasan_sertifika = (
        await db.scalar(
            select(func.count())
            .select_from(Sertifika)
            .where(
                Sertifika.gecerlilik_tarihi.is_not(None),
                Sertifika.gecerlilik_tarihi >= bugun,
                Sertifika.gecerlilik_tarihi <= sinir,
            )
        )
        or 0
    )
    acik_zimmet = (
        await db.scalar(select(func.count()).select_from(Zimmet).where(Zimmet.durum == "zimmetli"))
        or 0
    )

    ozet = IkOzetDTO(
        aktif_personel=int(aktif),
        toplam_personel=int(toplam),
        bugun_izinli=int(bugun_izinli),
        yaklasan_sertifika=int(yaklasan_sertifika),
        acik_zimmet=int(acik_zimmet),
    )
    return basari(ozet.model_dump(), mesaj="İK özeti")
