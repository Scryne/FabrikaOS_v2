"""Kalite uçları (``/api/v1``) — denetim + Tam CAPA.

Tüm uçlar tenant-kapsamlı + RBAC (``kalite:oku``/``kalite:yaz``); yazma işlemleri audit'lenir.
Uygunsuzluk + CAPA uçları sonraki task'ta eklenir.
"""

from __future__ import annotations

from datetime import UTC, datetime
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
from app.core.olaylar import olay_yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.kalite import durum, repository, service
from app.modules.kalite.birimler import (
    CAPA_AKSIYON_DURUMLARI,
    CAPA_AKSIYON_TURLERI,
    KONTROL_SONUCLARI,
    KONTROL_TURLERI,
    UYGUNSUZLUK_ONEMLERI,
)
from app.modules.kalite.models import CapaAksiyon, KaliteKontrol, Uygunsuzluk
from app.modules.kalite.schemas import (
    AksiyonCevapDTO,
    AksiyonGuncelleDTO,
    AksiyonOlusturDTO,
    DurumGecisDTO,
    KaliteKontrolCevapDTO,
    KaliteKontrolOlusturDTO,
    KaliteOzetDTO,
    UygunsuzlukCevapDTO,
    UygunsuzlukDetayDTO,
    UygunsuzlukGuncelleDTO,
    UygunsuzlukOlusturDTO,
)

router = APIRouter(tags=["Kalite"])


def _kontrol_cevap(k: KaliteKontrol) -> dict[str, Any]:
    return KaliteKontrolCevapDTO(
        id=k.id,
        kod=k.kod,
        makine_id=k.makine_id,
        is_emri_id=k.is_emri_id,
        kontrol_turu=k.kontrol_turu,
        sonuc=k.sonuc,
        olculen_deger=float(k.olculen_deger) if k.olculen_deger is not None else None,
        alt_limit=float(k.alt_limit) if k.alt_limit is not None else None,
        ust_limit=float(k.ust_limit) if k.ust_limit is not None else None,
        numune_adedi=k.numune_adedi,
        uygunsuz_adet=k.uygunsuz_adet,
        aciklama=k.aciklama,
        kontrol_eden_kullanici_id=k.kontrol_eden_kullanici_id,
        zaman=k.zaman,
    ).model_dump()


def _kontrol_dogrula(govde: KaliteKontrolOlusturDTO) -> None:
    if govde.sonuc not in KONTROL_SONUCLARI:
        raise DogrulamaHatasi(
            "Geçersiz sonuç",
            detaylar=[
                {"alan": "sonuc", "mesaj": f"Geçerli: {', '.join(sorted(KONTROL_SONUCLARI))}"}
            ],
        )
    if govde.kontrol_turu not in KONTROL_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz kontrol türü",
            detaylar=[
                {
                    "alan": "kontrol_turu",
                    "mesaj": f"Geçerli: {', '.join(sorted(KONTROL_TURLERI))}",
                }
            ],
        )
    if govde.uygunsuz_adet > govde.numune_adedi:
        raise DogrulamaHatasi(
            "Uygunsuz adet numune adedini aşamaz",
            detaylar=[
                {"alan": "uygunsuz_adet", "mesaj": f"<= numune_adedi ({govde.numune_adedi})"}
            ],
        )
    if (
        govde.alt_limit is not None
        and govde.ust_limit is not None
        and govde.alt_limit > govde.ust_limit
    ):
        raise DogrulamaHatasi(
            "alt_limit ust_limit'ten büyük olamaz",
            detaylar=[{"alan": "alt_limit", "mesaj": "<= ust_limit"}],
        )


@router.post(
    "/kalite-kontrolleri",
    response_model=Zarf[KaliteKontrolCevapDTO],
    status_code=201,
    summary="Kalite kontrol kaydı oluştur",
)
async def kontrol_olustur(
    govde: KaliteKontrolOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _kontrol_dogrula(govde)
    kontrol = KaliteKontrol(
        kod=service.kalite_kontrol_gecici_kod(),
        makine_id=govde.makine_id,
        is_emri_id=govde.is_emri_id,
        kontrol_turu=govde.kontrol_turu,
        sonuc=govde.sonuc,
        olculen_deger=govde.olculen_deger,
        alt_limit=govde.alt_limit,
        ust_limit=govde.ust_limit,
        numune_adedi=govde.numune_adedi,
        uygunsuz_adet=govde.uygunsuz_adet,
        aciklama=govde.aciklama,
        kontrol_eden_kullanici_id=kullanici.id,
        **({"zaman": govde.zaman} if govde.zaman is not None else {}),
    )
    await repository.kontrol_ekle(db, kontrol)
    kontrol.kod = service.kalite_kontrol_kalici_kod(kontrol.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="kalite_kontrol", kaynak_id=str(kontrol.id), kullanici=kullanici
    )
    await yayinla(tenant.slug, {"tur": "kalite.kontrol", "id": kontrol.id})
    return basari(_kontrol_cevap(kontrol), mesaj="Kalite kontrol oluşturuldu")


@router.get(
    "/kalite-kontrolleri",
    response_model=Zarf[list[KaliteKontrolCevapDTO]],
    summary="Kalite kontrolleri listele",
)
async def kontrol_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    makine_id: int | None = None,
    sonuc: str | None = None,
    arama: str | None = None,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.kontrol_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        makine_id=makine_id,
        sonuc=sonuc,
        arama=arama,
        baslangic=baslangic,
        bitis=bitis,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_kontrol_cevap(k) for k in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/kalite-kontrolleri/{kontrol_id}",
    response_model=Zarf[KaliteKontrolCevapDTO],
    summary="Kalite kontrol detayı",
)
async def kontrol_detay(
    kontrol_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kontrol = await repository.kontrol_getir(db, kontrol_id)
    if kontrol is None:
        raise KaynakBulunamadi("Kalite kontrol bulunamadı")
    return basari(_kontrol_cevap(kontrol), mesaj="Kalite kontrol detayı")


def _aksiyon_cevap(a: CapaAksiyon) -> dict[str, Any]:
    return AksiyonCevapDTO(
        id=a.id,
        tur=a.tur,
        aciklama=a.aciklama,
        sorumlu_kullanici_id=a.sorumlu_kullanici_id,
        termin_tarihi=a.termin_tarihi,
        durum=a.durum,
        tamamlanma_tarihi=a.tamamlanma_tarihi,
    ).model_dump()


def _uygunsuzluk_cevap(u: Uygunsuzluk) -> dict[str, Any]:
    return UygunsuzlukCevapDTO(
        id=u.id,
        kod=u.kod,
        baslik=u.baslik,
        aciklama=u.aciklama,
        kaynak_kontrol_id=u.kaynak_kontrol_id,
        makine_id=u.makine_id,
        onem=u.onem,
        durum=u.durum,
        kok_neden=u.kok_neden,
        acan_kullanici_id=u.acan_kullanici_id,
        sorumlu_kullanici_id=u.sorumlu_kullanici_id,
        dogrulama_notu=u.dogrulama_notu,
        kapanis_tarihi=u.kapanis_tarihi,
        olusturma_tarihi=u.olusturma_tarihi,
    ).model_dump()


def _uygunsuzluk_detay_cevap(u: Uygunsuzluk) -> dict[str, Any]:
    return UygunsuzlukDetayDTO(
        id=u.id,
        kod=u.kod,
        baslik=u.baslik,
        aciklama=u.aciklama,
        kaynak_kontrol_id=u.kaynak_kontrol_id,
        makine_id=u.makine_id,
        onem=u.onem,
        durum=u.durum,
        kok_neden=u.kok_neden,
        acan_kullanici_id=u.acan_kullanici_id,
        sorumlu_kullanici_id=u.sorumlu_kullanici_id,
        dogrulama_notu=u.dogrulama_notu,
        kapanis_tarihi=u.kapanis_tarihi,
        olusturma_tarihi=u.olusturma_tarihi,
        aksiyonlar=[AksiyonCevapDTO(**_aksiyon_cevap(a)) for a in u.aksiyonlar],
    ).model_dump()


def _onem_dogrula(onem: str) -> None:
    if onem not in UYGUNSUZLUK_ONEMLERI:
        raise DogrulamaHatasi(
            "Geçersiz önem",
            detaylar=[
                {"alan": "onem", "mesaj": f"Geçerli: {', '.join(sorted(UYGUNSUZLUK_ONEMLERI))}"}
            ],
        )


@router.post(
    "/uygunsuzluklar",
    response_model=Zarf[UygunsuzlukDetayDTO],
    status_code=201,
    summary="Uygunsuzluk (CAPA) oluştur",
)
async def uygunsuzluk_olustur(
    govde: UygunsuzlukOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _onem_dogrula(govde.onem)
    if govde.kaynak_kontrol_id is not None and (
        await repository.kontrol_getir(db, govde.kaynak_kontrol_id) is None
    ):
        raise KaynakBulunamadi("Kaynak kalite kontrol bulunamadı")
    u = Uygunsuzluk(
        kod=service.uygunsuzluk_gecici_kod(),
        baslik=govde.baslik,
        aciklama=govde.aciklama,
        onem=govde.onem,
        kaynak_kontrol_id=govde.kaynak_kontrol_id,
        makine_id=govde.makine_id,
        sorumlu_kullanici_id=govde.sorumlu_kullanici_id,
        acan_kullanici_id=kullanici.id,
    )
    await repository.uygunsuzluk_ekle(db, u)
    u.kod = service.uygunsuzluk_kalici_kod(u.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="uygunsuzluk", kaynak_id=str(u.id), kullanici=kullanici
    )
    await olay_yayinla(
        db,
        olay_turu="kalite.uygunsuzluk",
        govde={
            "uygunsuzluk_id": u.id,
            "kod": u.kod,
            "baslik": u.baslik,
            "onem": u.onem,
            "durum": u.durum,
        },
    )
    await yayinla(tenant.slug, {"tur": "kalite.uygunsuzluk", "id": u.id, "durum": u.durum})
    tam = await repository.uygunsuzluk_getir_aksiyonlu(db, u.id)
    assert tam is not None
    return basari(_uygunsuzluk_detay_cevap(tam), mesaj="Uygunsuzluk oluşturuldu")


@router.get(
    "/uygunsuzluklar",
    response_model=Zarf[list[UygunsuzlukCevapDTO]],
    summary="Uygunsuzlukları listele",
)
async def uygunsuzluk_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    durum: str | None = None,
    onem: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.uygunsuzluk_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        durum=durum,
        onem=onem,
        arama=arama,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_uygunsuzluk_cevap(u) for u in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/uygunsuzluklar/{uygunsuzluk_id}",
    response_model=Zarf[UygunsuzlukDetayDTO],
    summary="Uygunsuzluk detayı (aksiyonlarla)",
)
async def uygunsuzluk_detay(
    uygunsuzluk_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    u = await repository.uygunsuzluk_getir_aksiyonlu(db, uygunsuzluk_id)
    if u is None:
        raise KaynakBulunamadi("Uygunsuzluk bulunamadı")
    return basari(_uygunsuzluk_detay_cevap(u), mesaj="Uygunsuzluk detayı")


@router.patch(
    "/uygunsuzluklar/{uygunsuzluk_id}",
    response_model=Zarf[UygunsuzlukDetayDTO],
    summary="Uygunsuzluk düzenle (yalnız aktif durumlar)",
)
async def uygunsuzluk_guncelle(
    uygunsuzluk_id: int,
    govde: UygunsuzlukGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    u = await repository.uygunsuzluk_getir(db, uygunsuzluk_id)
    if u is None:
        raise KaynakBulunamadi("Uygunsuzluk bulunamadı")
    if u.durum in durum.TERMINAL_DURUMLAR:
        raise CakismaHatasi("Terminal durumda uygunsuzluk düzenlenemez")
    if govde.onem is not None:
        _onem_dogrula(govde.onem)
        u.onem = govde.onem
    for alan in ("baslik", "aciklama", "sorumlu_kullanici_id"):
        deger = getattr(govde, alan)
        if deger is not None:
            setattr(u, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="uygunsuzluk", kaynak_id=str(u.id), kullanici=kullanici
    )
    tam = await repository.uygunsuzluk_getir_aksiyonlu(db, u.id)
    assert tam is not None
    return basari(_uygunsuzluk_detay_cevap(tam), mesaj="Uygunsuzluk güncellendi")


@router.patch(
    "/uygunsuzluklar/{uygunsuzluk_id}/durum",
    response_model=Zarf[UygunsuzlukCevapDTO],
    summary="CAPA durum geçişi",
)
async def uygunsuzluk_durum(
    uygunsuzluk_id: int,
    govde: DurumGecisDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    u = await repository.uygunsuzluk_getir_kilitli(db, uygunsuzluk_id)
    if u is None:
        raise KaynakBulunamadi("Uygunsuzluk bulunamadı")
    await service.capa_durum_gecisi(
        db, u, hedef=govde.hedef, kok_neden=govde.kok_neden, dogrulama_notu=govde.dogrulama_notu
    )
    await denetim_yaz(
        db,
        eylem="durum_guncelle",
        kaynak="uygunsuzluk",
        kaynak_id=str(u.id),
        kullanici=kullanici,
        detay={"durum": u.durum},
    )
    await yayinla(tenant.slug, {"tur": "kalite.uygunsuzluk", "id": u.id, "durum": u.durum})
    return basari(_uygunsuzluk_cevap(u), mesaj="Durum güncellendi")


@router.post(
    "/uygunsuzluklar/{uygunsuzluk_id}/aksiyonlar",
    response_model=Zarf[UygunsuzlukDetayDTO],
    status_code=201,
    summary="CAPA aksiyonu ekle (düzeltici/önleyici)",
)
async def aksiyon_ekle(
    uygunsuzluk_id: int,
    govde: AksiyonOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    u = await repository.uygunsuzluk_getir(db, uygunsuzluk_id)
    if u is None:
        raise KaynakBulunamadi("Uygunsuzluk bulunamadı")
    if govde.tur not in CAPA_AKSIYON_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz aksiyon türü",
            detaylar=[
                {"alan": "tur", "mesaj": f"Geçerli: {', '.join(sorted(CAPA_AKSIYON_TURLERI))}"}
            ],
        )
    aksiyon = CapaAksiyon(
        uygunsuzluk_id=u.id,
        tur=govde.tur,
        aciklama=govde.aciklama,
        sorumlu_kullanici_id=govde.sorumlu_kullanici_id,
        termin_tarihi=govde.termin_tarihi,
    )
    db.add(aksiyon)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="aksiyon_ekle",
        kaynak="uygunsuzluk",
        kaynak_id=str(u.id),
        kullanici=kullanici,
        detay={"aksiyon_id": aksiyon.id, "tur": aksiyon.tur},
    )
    tam = await repository.uygunsuzluk_getir_aksiyonlu(db, u.id)
    assert tam is not None
    return basari(_uygunsuzluk_detay_cevap(tam), mesaj="Aksiyon eklendi")


@router.patch(
    "/uygunsuzluklar/{uygunsuzluk_id}/aksiyonlar/{aksiyon_id}",
    response_model=Zarf[UygunsuzlukDetayDTO],
    summary="CAPA aksiyonu güncelle",
)
async def aksiyon_guncelle(
    uygunsuzluk_id: int,
    aksiyon_id: int,
    govde: AksiyonGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    aksiyon = await repository.aksiyon_getir(db, aksiyon_id)
    if aksiyon is None or aksiyon.uygunsuzluk_id != uygunsuzluk_id:
        raise KaynakBulunamadi("Aksiyon bulunamadı")
    if govde.durum is not None:
        if govde.durum not in CAPA_AKSIYON_DURUMLARI:
            raise DogrulamaHatasi(
                "Geçersiz aksiyon durumu",
                detaylar=[
                    {
                        "alan": "durum",
                        "mesaj": f"Geçerli: {', '.join(sorted(CAPA_AKSIYON_DURUMLARI))}",
                    }
                ],
            )
        aksiyon.durum = govde.durum
        aksiyon.tamamlanma_tarihi = datetime.now(UTC) if govde.durum == "tamamlandi" else None
    for alan in ("aciklama", "sorumlu_kullanici_id", "termin_tarihi"):
        deger = getattr(govde, alan)
        if deger is not None:
            setattr(aksiyon, alan, deger)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="aksiyon_guncelle",
        kaynak="uygunsuzluk",
        kaynak_id=str(uygunsuzluk_id),
        kullanici=kullanici,
        detay={"aksiyon_id": aksiyon.id},
    )
    tam = await repository.uygunsuzluk_getir_aksiyonlu(db, uygunsuzluk_id)
    assert tam is not None
    return basari(_uygunsuzluk_detay_cevap(tam), mesaj="Aksiyon güncellendi")


@router.get("/kalite/ozet", response_model=Zarf[KaliteOzetDTO], summary="Kalite/CAPA özeti (KPI)")
async def kalite_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kalite:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    durum_sonuc = await db.execute(
        select(Uygunsuzluk.durum, func.count()).group_by(Uygunsuzluk.durum)
    )
    sayac: dict[str, int] = {}
    for d, adet in durum_sonuc.all():
        sayac[d] = int(adet)

    ay_basi = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    bu_ay = (
        await db.scalar(
            select(func.count())
            .select_from(Uygunsuzluk)
            .where(Uygunsuzluk.durum == "kapandi", Uygunsuzluk.kapanis_tarihi >= ay_basi)
        )
        or 0
    )

    toplam_kontrol = await db.scalar(select(func.count()).select_from(KaliteKontrol)) or 0
    gecti = (
        await db.scalar(
            select(func.count()).select_from(KaliteKontrol).where(KaliteKontrol.sonuc == "gecti")
        )
        or 0
    )

    ozet = KaliteOzetDTO(
        acik_uygunsuzluk=sayac.get("acik", 0),
        dogrulamada=sayac.get("dogrulama", 0),
        kapali_uygunsuzluk=sayac.get("kapandi", 0),
        bu_ay_kapanan=int(bu_ay),
        toplam_uygunsuzluk=sum(sayac.values()),
        toplam_kontrol=int(toplam_kontrol),
        gecti_kontrol=int(gecti),
        gecti_orani=(int(gecti) / int(toplam_kontrol)) if toplam_kontrol else 0.0,
    )
    return basari(ozet.model_dump(), mesaj="Kalite özeti")
