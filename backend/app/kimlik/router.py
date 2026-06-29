"""Kimlik uçları: ``/api/v1/kimlik/{token,yenile,cikis,ben,parola-degistir}``.

``token`` ucu kimlik gerektirmez ama tenant çözümlemesi gerektirir (kullanıcı doğru
şemada aranır) ve rate-limit'lidir. Diğer uçlar ``mevcut_kullanici`` ile korunur.
Tüm yanıtlar standart başarı zarfıyla döner.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import Tenant
from app.core.db.session import get_session
from app.core.deps import mevcut_kullanici, tenant_cozumle
from app.core.exceptions import AppError
from app.core.responses import Zarf, basari
from app.core.security.ratelimit import rate_limit_kontrol
from app.kimlik import service
from app.kimlik.models import Kullanici
from app.kimlik.schemas import (
    BenCevapDTO,
    CikisGirdiDTO,
    ParolaDegistirDTO,
    TokenCevapDTO,
    YenileGirdiDTO,
)

router = APIRouter(prefix="/kimlik", tags=["Kimlik"])


def _token_zarfi(access: str, refresh: str, mesaj: str) -> dict[str, Any]:
    return basari(
        TokenCevapDTO(access_token=access, refresh_token=refresh).model_dump(), mesaj=mesaj
    )


@router.post("/token", response_model=Zarf[TokenCevapDTO], summary="Giriş (OAuth2 şifre akışı)")
async def token(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    ip = request.client.host if request.client else "bilinmiyor"
    sonuc = await rate_limit_kontrol(f"giris:{tenant.slug}:{ip}")
    if not sonuc.izinli:
        raise AppError(
            "Çok fazla giriş denemesi, lütfen sonra tekrar deneyin",
            hata_kodu="RATE_LIMIT",
            durum_kodu=429,
        )
    access, refresh = await service.giris_yap(
        db, tenant, eposta=form.username, parola=form.password
    )
    return _token_zarfi(access, refresh, "Giriş başarılı")


@router.post("/yenile", response_model=Zarf[TokenCevapDTO], summary="Token yenileme (rotasyon)")
async def yenile(
    govde: YenileGirdiDTO,
    tenant: Annotated[Tenant, Depends(tenant_cozumle)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    access, refresh = await service.token_yenile(db, tenant, refresh_token=govde.refresh_token)
    return _token_zarfi(access, refresh, "Token yenilendi")


@router.post("/cikis", response_model=Zarf[None], summary="Çıkış (refresh iptal)")
async def cikis(
    govde: CikisGirdiDTO,
    _kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
) -> dict[str, Any]:
    await service.cikis(refresh_token=govde.refresh_token)
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
    )
    return basari(veri.model_dump(), mesaj="Kullanıcı bilgisi")


@router.post("/parola-degistir", response_model=Zarf[None], summary="Parola değiştirme")
async def parola_degistir(
    govde: ParolaDegistirDTO,
    kullanici: Annotated[Kullanici, Depends(mevcut_kullanici)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    await service.parola_degistir(
        db, kullanici, eski_parola=govde.eski_parola, yeni_parola=govde.yeni_parola
    )
    return basari(None, mesaj="Parola değiştirildi")
