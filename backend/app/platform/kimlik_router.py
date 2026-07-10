"""Platform kimlik uçları: ``/api/v1/platform/kimlik/{token,yenile,cikis,ben}``.

Tenant ``kimlik/router.py``'sinin control-plane aynası — tenant çözümlemesi YOK,
rate limit anahtarı ``giris:platform:<ip>``.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import PlatformYonetici
from app.core.db.session import get_session
from app.core.exceptions import AppError
from app.core.responses import Zarf, basari
from app.core.security.ratelimit import rate_limit_kontrol
from app.kimlik.schemas import CikisGirdiDTO, TokenCevapDTO, YenileGirdiDTO
from app.platform import kimlik_service
from app.platform.deps import mevcut_platform_yonetici
from app.platform.schemas import PlatformBenCevapDTO

router = APIRouter(prefix="/platform/kimlik", tags=["Platform"])


def _token_zarfi(access: str, refresh: str, mesaj: str) -> dict[str, Any]:
    return basari(
        TokenCevapDTO(access_token=access, refresh_token=refresh).model_dump(), mesaj=mesaj
    )


@router.post(
    "/token", response_model=Zarf[TokenCevapDTO], summary="Platform girişi (OAuth2 şifre akışı)"
)
async def token(
    request: Request,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    ip = request.client.host if request.client else "bilinmiyor"
    sonuc = await rate_limit_kontrol(f"giris:platform:{ip}")
    if not sonuc.izinli:
        raise AppError(
            "Çok fazla giriş denemesi, lütfen sonra tekrar deneyin",
            hata_kodu="RATE_LIMIT",
            durum_kodu=429,
        )
    access, refresh = await kimlik_service.platform_giris(
        db, eposta=form.username, parola=form.password
    )
    return _token_zarfi(access, refresh, "Giriş başarılı")


@router.post(
    "/yenile", response_model=Zarf[TokenCevapDTO], summary="Platform token yenileme (rotasyon)"
)
async def yenile(
    govde: YenileGirdiDTO,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    access, refresh = await kimlik_service.platform_token_yenile(
        db, refresh_token=govde.refresh_token
    )
    return _token_zarfi(access, refresh, "Token yenilendi")


@router.post("/cikis", response_model=Zarf[None], summary="Platform çıkışı (refresh iptal)")
async def cikis(
    govde: CikisGirdiDTO,
    _yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
) -> dict[str, Any]:
    await kimlik_service.platform_cikis(refresh_token=govde.refresh_token)
    return basari(None, mesaj="Çıkış yapıldı")


@router.get("/ben", response_model=Zarf[PlatformBenCevapDTO], summary="Oturum açan yönetici")
async def ben(
    yonetici: Annotated[PlatformYonetici, Depends(mevcut_platform_yonetici)],
) -> dict[str, Any]:
    veri = PlatformBenCevapDTO(
        id=yonetici.id,
        eposta=yonetici.eposta,
        ad_soyad=yonetici.ad_soyad,
        son_giris_tarihi=yonetici.son_giris_tarihi,
    )
    return basari(veri.model_dump(), mesaj="Yönetici bilgisi")
