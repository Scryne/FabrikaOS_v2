"""İSG uçları (``/api/v1``) — iş kazası + risk değerlendirme (risk matrisi).

Tüm uçlar tenant-kapsamlı + RBAC (``isg:oku``/``isg:yaz``); yazma işlemleri audit'lenir.
İş kazası açılışında transactional outbox ``isg.kaza`` (İSG olayları webhook için kritiktir)
+ realtime yayını yapılır. Risk skoru/seviyesi sunucuda ``risk_matrisi`` ile hesaplanır.
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
from app.core.exceptions import DogrulamaHatasi, KaynakBulunamadi
from app.core.gercekzaman import yayinla
from app.core.olaylar import olay_yayinla
from app.core.responses import Zarf, basari, sayfali
from app.kimlik.models import Kullanici
from app.modules.isg import repository, risk_matrisi, service
from app.modules.isg.birimler import KAZA_AGIRLIKLARI, KAZA_TURLERI, RISK_DURUMLARI
from app.modules.isg.models import IsKazasi, RiskDegerlendirme
from app.modules.isg.schemas import (
    IsgOzetDTO,
    IsKazasiCevapDTO,
    IsKazasiGuncelleDTO,
    IsKazasiOlusturDTO,
    RiskDegerlendirmeCevapDTO,
    RiskDegerlendirmeGuncelleDTO,
    RiskDegerlendirmeOlusturDTO,
    RiskHucreDTO,
)

router = APIRouter(tags=["İSG"])


# --- İş kazası ---
def _kaza_cevap(k: IsKazasi) -> dict[str, Any]:
    return IsKazasiCevapDTO(
        id=k.id,
        kod=k.kod,
        tur=k.tur,
        olay_tarihi=k.olay_tarihi,
        yer=k.yer,
        aciklama=k.aciklama,
        agirlik=k.agirlik,
        kaybedilen_gun=k.kaybedilen_gun,
        yaralanma_turu=k.yaralanma_turu,
        personel_id=k.personel_id,
        makine_id=k.makine_id,
        raporlayan_kullanici_id=k.raporlayan_kullanici_id,
        olusturma_tarihi=k.olusturma_tarihi,
    ).model_dump()


def _kaza_dogrula(tur: str, agirlik: str) -> None:
    if tur not in KAZA_TURLERI:
        raise DogrulamaHatasi(
            "Geçersiz kaza türü",
            detaylar=[{"alan": "tur", "mesaj": f"Geçerli: {', '.join(sorted(KAZA_TURLERI))}"}],
        )
    if agirlik not in KAZA_AGIRLIKLARI:
        raise DogrulamaHatasi(
            "Geçersiz ağırlık",
            detaylar=[
                {"alan": "agirlik", "mesaj": f"Geçerli: {', '.join(sorted(KAZA_AGIRLIKLARI))}"}
            ],
        )


@router.post(
    "/is-kazalari",
    response_model=Zarf[IsKazasiCevapDTO],
    status_code=201,
    summary="İş kazası / ramak-kala kaydı oluştur",
)
async def kaza_olustur(
    govde: IsKazasiOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("isg:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _kaza_dogrula(govde.tur, govde.agirlik)
    kaza = IsKazasi(
        kod=service.kaza_gecici_kod(),
        tur=govde.tur,
        yer=govde.yer,
        aciklama=govde.aciklama,
        agirlik=govde.agirlik,
        kaybedilen_gun=govde.kaybedilen_gun,
        yaralanma_turu=govde.yaralanma_turu,
        personel_id=govde.personel_id,
        makine_id=govde.makine_id,
        raporlayan_kullanici_id=kullanici.id,
        **({"olay_tarihi": govde.olay_tarihi} if govde.olay_tarihi is not None else {}),
    )
    await repository.kaza_ekle(db, kaza)
    kaza.kod = service.kaza_kalici_kod(kaza.id)
    await db.flush()
    await denetim_yaz(
        db, eylem="olustur", kaynak="is_kazasi", kaynak_id=str(kaza.id), kullanici=kullanici
    )
    await olay_yayinla(
        db,
        olay_turu="isg.kaza",
        govde={"kaza_id": kaza.id, "kod": kaza.kod, "tur": kaza.tur, "agirlik": kaza.agirlik},
    )
    await yayinla(tenant.slug, {"tur": "isg.kaza", "id": kaza.id})
    return basari(_kaza_cevap(kaza), mesaj="İş kazası kaydı oluşturuldu")


@router.get(
    "/is-kazalari",
    response_model=Zarf[list[IsKazasiCevapDTO]],
    summary="İş kazalarını listele",
)
async def kaza_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("isg:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    tur: str | None = None,
    agirlik: str | None = None,
    personel_id: int | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.kaza_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        tur=tur,
        agirlik=agirlik,
        personel_id=personel_id,
        arama=arama,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_kaza_cevap(k) for k in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/is-kazalari/{kaza_id}",
    response_model=Zarf[IsKazasiCevapDTO],
    summary="İş kazası detayı",
)
async def kaza_detay(
    kaza_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("isg:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kaza = await repository.kaza_getir(db, kaza_id)
    if kaza is None:
        raise KaynakBulunamadi("İş kazası bulunamadı")
    return basari(_kaza_cevap(kaza), mesaj="İş kazası detayı")


@router.patch(
    "/is-kazalari/{kaza_id}",
    response_model=Zarf[IsKazasiCevapDTO],
    summary="İş kazası düzenle",
)
async def kaza_guncelle(
    kaza_id: int,
    govde: IsKazasiGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("isg:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    kaza = await repository.kaza_getir(db, kaza_id)
    if kaza is None:
        raise KaynakBulunamadi("İş kazası bulunamadı")
    if govde.agirlik is not None and govde.agirlik not in KAZA_AGIRLIKLARI:
        raise DogrulamaHatasi(
            "Geçersiz ağırlık",
            detaylar=[
                {"alan": "agirlik", "mesaj": f"Geçerli: {', '.join(sorted(KAZA_AGIRLIKLARI))}"}
            ],
        )
    for alan in (
        "yer",
        "aciklama",
        "agirlik",
        "kaybedilen_gun",
        "yaralanma_turu",
        "personel_id",
        "makine_id",
    ):
        deger = getattr(govde, alan)
        if deger is not None:
            setattr(kaza, alan, deger)
    await db.flush()
    await denetim_yaz(
        db, eylem="guncelle", kaynak="is_kazasi", kaynak_id=str(kaza.id), kullanici=kullanici
    )
    return basari(_kaza_cevap(kaza), mesaj="İş kazası güncellendi")


# --- Risk değerlendirme ---
def _risk_cevap(r: RiskDegerlendirme) -> dict[str, Any]:
    return RiskDegerlendirmeCevapDTO(
        id=r.id,
        kod=r.kod,
        baslik=r.baslik,
        bolum=r.bolum,
        tehlike=r.tehlike,
        olasilik=r.olasilik,
        siddet=r.siddet,
        risk_skoru=r.risk_skoru,
        risk_seviyesi=r.risk_seviyesi,
        onlem=r.onlem,
        durum=r.durum,
        sorumlu_kullanici_id=r.sorumlu_kullanici_id,
        degerlendirme_tarihi=r.degerlendirme_tarihi,
        gecerlilik_tarihi=r.gecerlilik_tarihi,
        olusturma_tarihi=r.olusturma_tarihi,
    ).model_dump()


def _risk_durum_dogrula(durum: str) -> None:
    if durum not in RISK_DURUMLARI:
        raise DogrulamaHatasi(
            "Geçersiz durum",
            detaylar=[{"alan": "durum", "mesaj": f"Geçerli: {', '.join(sorted(RISK_DURUMLARI))}"}],
        )


@router.post(
    "/risk-degerlendirmeleri",
    response_model=Zarf[RiskDegerlendirmeCevapDTO],
    status_code=201,
    summary="Risk değerlendirme oluştur (risk matrisi)",
)
async def risk_olustur(
    govde: RiskDegerlendirmeOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("isg:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    _risk_durum_dogrula(govde.durum)
    skor = risk_matrisi.risk_skoru(govde.olasilik, govde.siddet)
    seviye = risk_matrisi.risk_seviyesi(skor)
    risk = RiskDegerlendirme(
        kod=service.risk_gecici_kod(),
        baslik=govde.baslik,
        bolum=govde.bolum,
        tehlike=govde.tehlike,
        olasilik=govde.olasilik,
        siddet=govde.siddet,
        risk_skoru=skor,
        risk_seviyesi=seviye,
        onlem=govde.onlem,
        durum=govde.durum,
        sorumlu_kullanici_id=govde.sorumlu_kullanici_id,
        gecerlilik_tarihi=govde.gecerlilik_tarihi,
    )
    await repository.risk_ekle(db, risk)
    risk.kod = service.risk_kalici_kod(risk.id)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="olustur",
        kaynak="risk_degerlendirme",
        kaynak_id=str(risk.id),
        kullanici=kullanici,
    )
    await yayinla(tenant.slug, {"tur": "isg.risk", "id": risk.id})
    return basari(_risk_cevap(risk), mesaj="Risk değerlendirme oluşturuldu")


@router.get(
    "/risk-degerlendirmeleri",
    response_model=Zarf[list[RiskDegerlendirmeCevapDTO]],
    summary="Risk değerlendirmeleri listele",
)
async def risk_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("isg:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
    sayfa: int = 1,
    adet: int = 20,
    durum: str | None = None,
    risk_seviyesi: str | None = None,
    arama: str | None = None,
    siralama: str | None = None,
    yon: str | None = None,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    kayitlar, toplam = await repository.risk_listele(
        db,
        sayfa=sayfa,
        adet=adet,
        durum=durum,
        risk_seviyesi=risk_seviyesi,
        arama=arama,
        siralama=siralama,
        yon=yon,
    )
    return sayfali([_risk_cevap(r) for r in kayitlar], sayfa=sayfa, adet=adet, toplam=toplam)


@router.get(
    "/risk-degerlendirmeleri/{risk_id}",
    response_model=Zarf[RiskDegerlendirmeCevapDTO],
    summary="Risk değerlendirme detayı",
)
async def risk_detay(
    risk_id: int,
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("isg:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    risk = await repository.risk_getir(db, risk_id)
    if risk is None:
        raise KaynakBulunamadi("Risk değerlendirme bulunamadı")
    return basari(_risk_cevap(risk), mesaj="Risk değerlendirme detayı")


@router.patch(
    "/risk-degerlendirmeleri/{risk_id}",
    response_model=Zarf[RiskDegerlendirmeCevapDTO],
    summary="Risk değerlendirme düzenle (skor/seviye yeniden hesaplanır)",
)
async def risk_guncelle(
    risk_id: int,
    govde: RiskDegerlendirmeGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("isg:yaz"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[object, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    risk = await repository.risk_getir(db, risk_id)
    if risk is None:
        raise KaynakBulunamadi("Risk değerlendirme bulunamadı")
    if govde.durum is not None:
        _risk_durum_dogrula(govde.durum)
        risk.durum = govde.durum
    for alan in (
        "baslik",
        "bolum",
        "tehlike",
        "onlem",
        "sorumlu_kullanici_id",
        "gecerlilik_tarihi",
    ):
        deger = getattr(govde, alan)
        if deger is not None:
            setattr(risk, alan, deger)
    if govde.olasilik is not None:
        risk.olasilik = govde.olasilik
    if govde.siddet is not None:
        risk.siddet = govde.siddet
    if govde.olasilik is not None or govde.siddet is not None:
        risk.risk_skoru = risk_matrisi.risk_skoru(risk.olasilik, risk.siddet)
        risk.risk_seviyesi = risk_matrisi.risk_seviyesi(risk.risk_skoru)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="guncelle",
        kaynak="risk_degerlendirme",
        kaynak_id=str(risk.id),
        kullanici=kullanici,
    )
    return basari(_risk_cevap(risk), mesaj="Risk değerlendirme güncellendi")


@router.get("/isg/ozet", response_model=Zarf[IsgOzetDTO], summary="İSG özeti (kaza + risk KPI)")
async def isg_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("isg:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    _tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    simdi = datetime.now(UTC)
    yil_basi = simdi.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

    son_kaza = await db.scalar(select(func.max(IsKazasi.olay_tarihi)).where(IsKazasi.tur == "kaza"))
    gunluk_kazasiz = (simdi - son_kaza).days if son_kaza is not None else -1
    bu_yil_kaza = (
        await db.scalar(
            select(func.count())
            .select_from(IsKazasi)
            .where(IsKazasi.tur == "kaza", IsKazasi.olay_tarihi >= yil_basi)
        )
        or 0
    )
    ramak_kala = (
        await db.scalar(
            select(func.count()).select_from(IsKazasi).where(IsKazasi.tur == "ramak_kala")
        )
        or 0
    )
    toplam_kayip_gun = (
        await db.scalar(select(func.coalesce(func.sum(IsKazasi.kaybedilen_gun), 0))) or 0
    )

    acik_risk = (
        await db.scalar(
            select(func.count())
            .select_from(RiskDegerlendirme)
            .where(RiskDegerlendirme.durum == "acik")
        )
        or 0
    )
    yuksek_risk = (
        await db.scalar(
            select(func.count())
            .select_from(RiskDegerlendirme)
            .where(RiskDegerlendirme.risk_seviyesi.in_(("yuksek", "cok_yuksek")))
        )
        or 0
    )
    toplam_risk = await db.scalar(select(func.count()).select_from(RiskDegerlendirme)) or 0

    matris_sonuc = await db.execute(
        select(RiskDegerlendirme.olasilik, RiskDegerlendirme.siddet, func.count()).group_by(
            RiskDegerlendirme.olasilik, RiskDegerlendirme.siddet
        )
    )
    matris = [
        RiskHucreDTO(olasilik=int(o), siddet=int(s), adet=int(a)) for o, s, a in matris_sonuc.all()
    ]

    ozet = IsgOzetDTO(
        gunluk_kazasiz=gunluk_kazasiz,
        bu_yil_kaza=int(bu_yil_kaza),
        ramak_kala=int(ramak_kala),
        toplam_kayip_gun=int(toplam_kayip_gun),
        acik_risk=int(acik_risk),
        yuksek_risk=int(yuksek_risk),
        toplam_risk=int(toplam_risk),
        risk_matrisi=matris,
    )
    return basari(ozet.model_dump(), mesaj="İSG özeti")
