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
from app.core.exceptions import CakismaHatasi, DogrulamaHatasi
from app.core.responses import Zarf, basari, sayfali
from app.core.security.parola import parola_ozetle
from app.kimlik.models import Kullanici, Rol
from app.kimlik.schemas import (
    KullaniciCevapDTO,
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
    # Koltuk (seat) limiti — S16/ADR-0018: eşzamanlı oluşturmalar public.tenant satırı
    # kilidiyle serileştirilir; aktif kullanıcı sayısı limiti aşamaz (pasifler sayılmaz).
    await db.execute(select(Tenant.id).where(Tenant.id == tenant.id).with_for_update())
    koltuk = await entitlement_service.koltuk_limiti_getir(db, tenant)
    if koltuk is not None:
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

    var = await db.scalar(select(Kullanici).where(Kullanici.eposta == govde.eposta))
    if var is not None:
        raise CakismaHatasi("Bu e-posta ile kullanıcı zaten var")

    roller: list[Rol] = []
    if govde.roller:
        bulunan = (await db.execute(select(Rol).where(Rol.ad.in_(govde.roller)))).scalars().all()
        eksik = set(govde.roller) - {r.ad for r in bulunan}
        if eksik:
            raise DogrulamaHatasi(
                "Tanımsız rol(ler)",
                detaylar=[{"alan": "roller", "mesaj": f"Bulunamadı: {', '.join(sorted(eksik))}"}],
            )
        roller = list(bulunan)

    yeni = Kullanici(
        eposta=govde.eposta,
        parola_ozet=parola_ozetle(govde.parola),
        ad_soyad=govde.ad_soyad,
        aktif=True,
        roller=roller,
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
