"""Kullanıcı yönetimi uçları: ``/api/v1/kullanicilar`` + ``/api/v1/roller``.

Tenant-kapsamlı ve RBAC korumalı (altın kural): GET ``kullanici:oku``, POST ``kullanici:yaz``;
rol kataloğu GET ``rol:oku``. Bu uçlar aynı zamanda tenant izolasyonu ve RBAC için
referans/test yüzeyidir.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.control_plane import entitlement_service
from app.control_plane.models import Tenant
from app.core.audit import denetim_yaz
from app.core.db.session import get_session
from app.core.deps import izin_gerekli, tenant_cozumle
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi, KaynakBulunamadi
from app.core.responses import Zarf, basari, sayfali
from app.core.security.parola import parola_ozetle
from app.kimlik.models import Kullanici, Rol
from app.kimlik.schemas import (
    KullaniciCevapDTO,
    KullaniciGuncelleDTO,
    KullaniciOlusturDTO,
    KullaniciOzetDTO,
    RolCevapDTO,
    RolSayiDTO,
)

router = APIRouter(prefix="/kullanicilar", tags=["Kullanıcılar"])
rol_router = APIRouter(prefix="/roller", tags=["Kullanıcılar"])


def _cevap(kullanici: Kullanici) -> dict[str, Any]:
    return KullaniciCevapDTO(
        id=kullanici.id,
        eposta=kullanici.eposta,
        ad_soyad=kullanici.ad_soyad,
        aktif=kullanici.aktif,
        roller=sorted(r.ad for r in kullanici.roller),
        firma_id=kullanici.firma_id,
    ).model_dump()


@router.get("", response_model=Zarf[list[KullaniciCevapDTO]], summary="Kullanıcıları listele")
async def listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kullanici:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
    sayfa: int = 1,
    adet: int = 20,
) -> dict[str, Any]:
    sayfa = max(sayfa, 1)
    adet = min(max(adet, 1), 100)
    toplam = await db.scalar(select(func.count()).select_from(Kullanici)) or 0
    sonuc = await db.execute(
        select(Kullanici).order_by(Kullanici.id).offset((sayfa - 1) * adet).limit(adet)
    )
    kayitlar = [_cevap(k) for k in sonuc.scalars()]
    return sayfali(kayitlar, sayfa=sayfa, adet=adet, toplam=int(toplam))


@router.get("/ozet", response_model=Zarf[KullaniciOzetDTO], summary="Kullanıcı özeti (KPI)")
async def kullanici_ozet(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("kullanici:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    sonuc = await db.execute(select(Kullanici).options(selectinload(Kullanici.roller)))
    kullanicilar = list(sonuc.scalars())
    toplam = len(kullanicilar)
    aktif = sum(1 for k in kullanicilar if k.aktif)
    rol_say: dict[str, int] = {}
    for k in kullanicilar:
        for r in k.roller:
            rol_say[r.ad] = rol_say.get(r.ad, 0) + 1
    rol_dagilimi = [
        RolSayiDTO(ad=ad, adet=adet)
        for ad, adet in sorted(rol_say.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    ozet = KullaniciOzetDTO(
        toplam=toplam,
        aktif=aktif,
        pasif=toplam - aktif,
        rol_sayisi=len(rol_say),
        rol_dagilimi=rol_dagilimi,
    )
    return basari(ozet.model_dump(), mesaj="Kullanıcı özeti")


async def _koltuk_kontrol(db: AsyncSession, tenant: Tenant) -> None:
    """Koltuk (seat) limiti — S16/ADR-0018: eşzamanlı yazmalar public.tenant satırı
    kilidiyle serileştirilir; aktif kullanıcı sayısı limiti aşamaz (pasifler sayılmaz)."""
    await db.execute(select(Tenant.id).where(Tenant.id == tenant.id).with_for_update())
    koltuk = await entitlement_service.koltuk_limiti_getir(db, tenant)
    if koltuk is None:
        return
    aktif_sayi = (
        await db.scalar(
            select(func.count()).select_from(Kullanici).where(Kullanici.aktif.is_(True))
        )
        or 0
    )
    if aktif_sayi >= koltuk:
        raise CakismaHatasi(
            f"Koltuk limiti doldu ({aktif_sayi}/{koltuk}) — plan yükseltin veya "
            "bir kullanıcıyı pasifleştirin",
            hata_kodu="KOLTUK_LIMITI",
        )


async def _roller_dogrula(db: AsyncSession, roller: list[str]) -> list[Rol]:
    """Rol adlarını tenant kataloğunda doğrular; tanımsız ad 422."""
    if not roller:
        return []
    bulunan = (await db.execute(select(Rol).where(Rol.ad.in_(roller)))).scalars().all()
    eksik = set(roller) - {r.ad for r in bulunan}
    if eksik:
        raise DogrulamaHatasi(
            "Tanımsız rol(ler)",
            detaylar=[{"alan": "roller", "mesaj": f"Bulunamadı: {', '.join(sorted(eksik))}"}],
        )
    return list(bulunan)


async def _firma_dogrula(db: AsyncSession, firma_id: int) -> None:
    """Dış portal firma bağlantısı (S18): verilen firma tenant şemasında var olmalı."""
    from app.modules.crm.repository import firma_getir

    if await firma_getir(db, firma_id) is None:
        raise DogrulamaHatasi(
            "Firma bulunamadı",
            detaylar=[{"alan": "firma_id", "mesaj": f"Firma yok: {firma_id}"}],
        )


@router.post(
    "",
    response_model=Zarf[KullaniciCevapDTO],
    status_code=201,
    summary="Kullanıcı oluştur",
)
async def olustur(
    govde: KullaniciOlusturDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kullanici:yaz"))],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    await _koltuk_kontrol(db, tenant)

    var = await db.scalar(select(Kullanici).where(Kullanici.eposta == govde.eposta))
    if var is not None:
        raise CakismaHatasi("Bu e-posta ile kullanıcı zaten var")

    roller = await _roller_dogrula(db, govde.roller)
    if govde.firma_id is not None:
        await _firma_dogrula(db, govde.firma_id)

    yeni = Kullanici(
        eposta=govde.eposta,
        parola_ozet=parola_ozetle(govde.parola),
        ad_soyad=govde.ad_soyad,
        aktif=True,
        roller=roller,
        firma_id=govde.firma_id,
    )
    db.add(yeni)
    await db.flush()
    await denetim_yaz(
        db,
        eylem="olustur",
        kaynak="kullanici",
        kaynak_id=str(yeni.id),
        kullanici=kullanici,
        detay={"eposta": yeni.eposta},
    )
    return basari(_cevap(yeni), mesaj="Kullanıcı oluşturuldu")


@router.patch(
    "/{kullanici_id}",
    response_model=Zarf[KullaniciCevapDTO],
    summary="Kullanıcı güncelle (ad/aktif/roller/firma)",
)
async def guncelle(
    kullanici_id: int,
    govde: KullaniciGuncelleDTO,
    kullanici: Annotated[Kullanici, Depends(izin_gerekli("kullanici:yaz"))],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Kısmi güncelleme. Kilitlenme koruması: kullanıcı KENDİ hesabının ``aktif``/``roller``
    alanlarını değiştiremez (tek admin kendini pasifleştirip tenant'ı kilitleyemesin).
    Yeniden aktifleştirme koltuk limitine tabidir (oluşturma ile aynı seri kontrol)."""
    hedef = await db.scalar(select(Kullanici).where(Kullanici.id == kullanici_id))
    if hedef is None:
        raise KaynakBulunamadi("Kullanıcı bulunamadı")

    degisenler = govde.model_dump(exclude_unset=True)
    if hedef.id == kullanici.id and ("aktif" in degisenler or "roller" in degisenler):
        raise DogrulamaHatasi(
            "Kendi hesabınızın aktifliğini veya rollerini değiştiremezsiniz",
            detaylar=[{"alan": "aktif", "mesaj": "Bu işlemi başka bir yönetici yapmalı"}],
        )

    if degisenler.get("aktif") is True and not hedef.aktif:
        # Pasif → aktif: koltuk açılıyor olabilir; limit oluşturmadaki gibi zorlanır.
        await _koltuk_kontrol(db, tenant)
    if "roller" in degisenler:
        hedef.roller = await _roller_dogrula(db, govde.roller or [])
    if "firma_id" in degisenler and govde.firma_id is not None:
        await _firma_dogrula(db, govde.firma_id)
    if "firma_id" in degisenler:
        hedef.firma_id = govde.firma_id
    if "ad_soyad" in degisenler and govde.ad_soyad is not None:
        hedef.ad_soyad = govde.ad_soyad
    if "aktif" in degisenler and govde.aktif is not None:
        hedef.aktif = govde.aktif

    await db.flush()
    await denetim_yaz(
        db,
        eylem="guncelle",
        kaynak="kullanici",
        kaynak_id=str(hedef.id),
        kullanici=kullanici,
        detay={"eposta": hedef.eposta, "degisenler": sorted(degisenler)},
    )
    return basari(_cevap(hedef), mesaj="Kullanıcı güncellendi")


@rol_router.get("", response_model=Zarf[list[RolCevapDTO]], summary="Rolleri listele")
async def rolleri_listele(
    _kullanici: Annotated[Kullanici, Depends(izin_gerekli("rol:oku"))],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Tenant'ın rol kataloğu — kullanıcı oluştururken rol seçimi için."""
    sonuc = await db.execute(select(Rol).order_by(Rol.ad))
    veri = [
        RolCevapDTO(
            id=r.id,
            ad=r.ad,
            aciklama=r.aciklama,
            izinler=sorted(i.kod for i in r.izinler),
        ).model_dump()
        for r in sonuc.scalars()
    ]
    return basari(veri, mesaj="Roller listelendi")
