"""Kimlik uçları: ``/api/v1/kimlik/{token,2fa-*,yenile,cikis,ben,parola-degistir,oturumlar}``.

``token`` ucu kimlik gerektirmez ama tenant çözümlemesi gerektirir (kullanıcı doğru
şemada aranır) ve rate-limit'lidir. 2FA kurulum uçları hem oturum (access) hem
zorunlu-kurulum geçici token'ı (tip ``2fa`` + ``kurulum``) kabul eder (S23/ADR-0022).
Tüm yanıtlar standart başarı zarfıyla döner.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.db.session import get_session
from app.core.deps import mevcut_kullanici, oauth2_scheme, tenant_cozumle
from app.core.exceptions import AppError, KimlikHatasi
from app.core.responses import Zarf, basari
from app.core.security import jwt as jwtmod
from app.core.security.ratelimit import rate_limit_kontrol
from app.kimlik import service, sso_service
from app.kimlik.models import Kullanici
from app.kimlik.schemas import (
    BenCevapDTO,
    CikisGirdiDTO,
    IkiAsamaDogrulaDTO,
    IkiAsamaEtkinlestirDTO,
    IkiAsamaKapatDTO,
    IkiAsamaKurCevapDTO,
    IkiAsamaKurtarmaCevapDTO,
    OturumCevapDTO,
    ParolaDegistirDTO,
    SsoBaslatCevapDTO,
    SsoDurumCevapDTO,
    SsoTamamlaDTO,
    TokenCevapDTO,
    YenileGirdiDTO,
)

router = APIRouter(prefix="/kimlik", tags=["Kimlik"])


def _istemci_bilgisi(request: Request) -> tuple[str | None, str]:
    ip = request.client.host if request.client else None
    return ip, request.headers.get("user-agent", "")[:300]


def _giris_zarfi(sonuc: service.GirisSonucu, mesaj: str) -> dict[str, Any]:
    return basari(
        TokenCevapDTO(
            access_token=sonuc.access,
            refresh_token=sonuc.refresh,
            iki_asama_gerekli=sonuc.iki_asama_gerekli,
            iki_asama_kurulum_gerekli=sonuc.iki_asama_kurulum_gerekli,
            gecici_token=sonuc.gecici_token,
        ).model_dump(),
        mesaj=mesaj,
    )


async def kimlik_veya_kurulum(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> Kullanici:
    """2FA kurulum uçları için kimlik: access token VEYA ``kurulum`` işaretli 2FA token'ı.

    Zorunlu-2FA tenant'ında kullanıcı henüz tam oturum açamaz; kurulum geçici token'la
    yapılır. Geçici token yalnız ``kurulum=true`` claim'i taşıyorsa kabul edilir.
    """
    if not token:
        raise KimlikHatasi("Kimlik doğrulaması gerekli")
    try:
        icerik = jwtmod.coz(token, "access")
    except jwtmod.TokenGecersiz:
        try:
            icerik = jwtmod.coz(token, "2fa")
        except jwtmod.TokenGecersiz as exc:
            raise KimlikHatasi("Geçersiz veya süresi dolmuş token") from exc
        # Yalnız kurulum-amaçlı geçici token kabul edilir (normal 2fa adımı DEĞİL).
        if not icerik.kurulum:
            raise KimlikHatasi("Bu adım için kurulum yetkisi yok") from None
    if icerik.tenant_slug != tenant.slug:
        raise KimlikHatasi("Token tenant'ı ile istek tenant'ı uyuşmuyor")
    kullanici = (
        await db.execute(select(Kullanici).where(Kullanici.id == icerik.kullanici_id))
    ).scalar_one_or_none()
    if kullanici is None or not kullanici.aktif:
        raise KimlikHatasi("Kullanıcı bulunamadı veya aktif değil")
    return kullanici


@router.post("/token", response_model=Zarf[TokenCevapDTO], summary="Giriş (OAuth2 şifre akışı)")
async def token(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    ip, istemci = _istemci_bilgisi(request)
    sonuc = await rate_limit_kontrol(f"giris:{tenant.slug}:{ip or 'bilinmiyor'}")
    if not sonuc.izinli:
        raise AppError(
            "Çok fazla giriş denemesi, lütfen sonra tekrar deneyin",
            hata_kodu="RATE_LIMIT",
            durum_kodu=429,
        )
    giris = await service.giris_yap(
        db, tenant, eposta=form.username, parola=form.password, ip=ip, istemci=istemci
    )
    if giris.iki_asama_gerekli:
        return _giris_zarfi(giris, "Doğrulama kodu gerekli")
    if giris.iki_asama_kurulum_gerekli:
        return _giris_zarfi(giris, "İki aşamalı doğrulama kurulumu gerekli")
    return _giris_zarfi(giris, "Giriş başarılı")


# --- Kurumsal SSO (OIDC Authorization Code + PKCE; S23 / ADR-0022) ---
@router.get(
    "/sso/durum",
    response_model=Zarf[SsoDurumCevapDTO],
    summary="Bu tenant'ta SSO açık mı (giriş ekranı için)",
)
async def sso_durum(
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    """Kimlik gerektirmez: giriş ekranı düğmeyi göstermek için sorar. Yalnız açık/kapalı
    bilgisi döner — issuer/istemci sırrı gibi yapılandırma detayı sızdırılmaz."""
    return basari(
        SsoDurumCevapDTO(aktif=sso_service.sso_acik_mi(tenant)).model_dump(),
        mesaj="SSO durumu",
    )


@router.post(
    "/sso/baslat",
    response_model=Zarf[SsoBaslatCevapDTO],
    summary="SSO akışını başlat (IdP yetkilendirme URL'i)",
)
async def sso_baslat(
    request: Request,
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
) -> dict[str, Any]:
    """``redirect_uri`` istemciden ALINMAZ; tenant yapılandırmasından gelir (açık
    yönlendirme koruması). Rate limit parola girişiyle aynı disiplinde."""
    ip, _ = _istemci_bilgisi(request)
    sonuc = await rate_limit_kontrol(f"sso:{tenant.slug}:{ip or 'bilinmiyor'}")
    if not sonuc.izinli:
        raise AppError(
            "Çok fazla deneme, lütfen sonra tekrar deneyin",
            hata_kodu="RATE_LIMIT",
            durum_kodu=429,
        )
    url = await sso_service.sso_baslat(tenant)
    return basari(SsoBaslatCevapDTO(yetkilendirme_url=url).model_dump(), mesaj="SSO başlatıldı")


@router.post(
    "/sso/tamamla",
    response_model=Zarf[TokenCevapDTO],
    summary="SSO dönüşünü tamamla (kod + state → oturum)",
)
async def sso_tamamla(
    request: Request,
    govde: SsoTamamlaDTO,
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    ip, istemci = _istemci_bilgisi(request)
    sonuc = await rate_limit_kontrol(f"sso:{tenant.slug}:{ip or 'bilinmiyor'}")
    if not sonuc.izinli:
        raise AppError(
            "Çok fazla deneme, lütfen sonra tekrar deneyin",
            hata_kodu="RATE_LIMIT",
            durum_kodu=429,
        )
    giris = await sso_service.sso_tamamla(
        db, tenant, kod=govde.kod, state=govde.state, ip=ip, istemci=istemci
    )
    if giris.iki_asama_gerekli:
        return _giris_zarfi(giris, "Doğrulama kodu gerekli")
    return _giris_zarfi(giris, "Giriş başarılı")


@router.post(
    "/2fa-dogrula",
    response_model=Zarf[TokenCevapDTO],
    summary="2FA ikinci adım (TOTP veya kurtarma kodu)",
)
async def iki_asama_dogrula(
    request: Request,
    govde: IkiAsamaDogrulaDTO,
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    ip, istemci = _istemci_bilgisi(request)
    sonuc = await rate_limit_kontrol(f"2fa:{tenant.slug}:{ip or 'bilinmiyor'}")
    if not sonuc.izinli:
        raise AppError(
            "Çok fazla deneme, lütfen sonra tekrar deneyin",
            hata_kodu="RATE_LIMIT",
            durum_kodu=429,
        )
    giris = await service.iki_asama_dogrula(
        db, tenant, gecici_token=govde.gecici_token, kod=govde.kod, ip=ip, istemci=istemci
    )
    return _giris_zarfi(giris, "Giriş başarılı")


@router.post(
    "/2fa-kur",
    response_model=Zarf[IkiAsamaKurCevapDTO],
    summary="2FA kurulumunu başlat (sır + QR URI)",
)
async def iki_asama_kur(
    kullanici: Annotated[Kullanici, Depends(kimlik_veya_kurulum)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    sir, uri = await service.iki_asama_kur(db, kullanici, tenant)
    return basari(
        IkiAsamaKurCevapDTO(sir=sir, otpauth_uri=uri).model_dump(),
        mesaj="Authenticator uygulamanıza ekleyin, sonra kodla etkinleştirin",
    )


@router.post(
    "/2fa-etkinlestir",
    response_model=Zarf[IkiAsamaKurtarmaCevapDTO],
    summary="2FA'yı etkinleştir (kod doğrulama + kurtarma kodları)",
)
async def iki_asama_etkinlestir(
    govde: IkiAsamaEtkinlestirDTO,
    kullanici: Annotated[Kullanici, Depends(kimlik_veya_kurulum)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    kodlar = await service.iki_asama_etkinlestir(db, kullanici, kod=govde.kod)
    return basari(
        IkiAsamaKurtarmaCevapDTO(kurtarma_kodlari=kodlar).model_dump(),
        mesaj="İki aşamalı doğrulama etkin — kurtarma kodlarını güvenle saklayın",
    )


@router.post("/2fa-kapat", response_model=Zarf[None], summary="2FA'yı kapat (parola + kod)")
async def iki_asama_kapat(
    govde: IkiAsamaKapatDTO,
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    await service.iki_asama_kapat(db, kullanici, parola=govde.parola, kod=govde.kod)
    return basari(None, mesaj="İki aşamalı doğrulama kapatıldı")


@router.post("/yenile", response_model=Zarf[TokenCevapDTO], summary="Token yenileme (rotasyon)")
async def yenile(
    govde: YenileGirdiDTO,
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    access, refresh = await service.token_yenile(db, tenant, refresh_token=govde.refresh_token)
    return basari(
        TokenCevapDTO(access_token=access, refresh_token=refresh).model_dump(),
        mesaj="Token yenilendi",
    )


@router.post("/cikis", response_model=Zarf[None], summary="Çıkış (refresh iptal)")
async def cikis(
    govde: CikisGirdiDTO,
    _kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    await service.cikis(db, refresh_token=govde.refresh_token)
    return basari(None, mesaj="Çıkış yapıldı")


@router.get("/ben", response_model=Zarf[BenCevapDTO], summary="Oturum açan kullanıcı")
async def ben(
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
) -> dict[str, Any]:
    veri = BenCevapDTO(
        id=kullanici.id,
        eposta=kullanici.eposta,
        ad_soyad=kullanici.ad_soyad,
        roller=sorted(r.ad for r in kullanici.roller),
        izinler=sorted(kullanici.izin_kodlari),
        son_giris_tarihi=kullanici.son_giris_tarihi,
        iki_asama_aktif=kullanici.iki_asama_aktif,
    )
    return basari(veri.model_dump(), mesaj="Kullanıcı bilgisi")


@router.post("/parola-degistir", response_model=Zarf[None], summary="Parola değiştirme")
async def parola_degistir(
    govde: ParolaDegistirDTO,
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    await service.parola_degistir(
        db,
        kullanici,
        eski_parola=govde.eski_parola,
        yeni_parola=govde.yeni_parola,
        tenant=tenant,
    )
    return basari(None, mesaj="Parola değiştirildi")


# --- Oturum / cihaz yönetimi (S23) ---
@router.get(
    "/oturumlar",
    response_model=Zarf[list[OturumCevapDTO]],
    summary="Aktif oturumlarım (cihaz listesi)",
)
async def oturumlar(
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    kayitlar = await service.oturumlar_listele(db, kullanici)
    return basari(
        [
            OturumCevapDTO(
                id=o.id,
                ip_adresi=o.ip_adresi,
                istemci=o.istemci,
                olusturma_tarihi=o.olusturma_tarihi,
                son_kullanim=o.son_kullanim,
                bitis=o.bitis,
            ).model_dump()
            for o in kayitlar
        ],
        mesaj="Aktif oturumlar",
    )


@router.delete(
    "/oturumlar/{oturum_id}",
    response_model=Zarf[None],
    summary="Oturumu uzaktan sonlandır",
)
async def oturum_sonlandir(
    oturum_id: int,
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    await service.oturum_sonlandir(db, kullanici, oturum_id)
    return basari(None, mesaj="Oturum sonlandırıldı")
