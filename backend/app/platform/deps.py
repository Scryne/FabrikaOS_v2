"""Platform düzlemi bağımlılıkları — ``mevcut_platform_yonetici``.

Tenant düzlemindeki ``mevcut_kullanici``'nın control-plane aynasıdır: token tipi
``platform_access`` olmak zorundadır (tenant access token'ı burada yapısal olarak
geçersizdir — 401). Tenant çözümlemesi ve ``search_path`` YOKTUR; sorgular
``PublicBase`` (schema="public") üzerinden çalışır.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import PlatformYonetici
from app.core.config import get_settings
from app.core.db.session import get_session
from app.core.exceptions import KimlikHatasi
from app.core.security import jwt as jwtmod

platform_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{get_settings().api_v1_prefix}/platform/kimlik/token", auto_error=False
)


async def mevcut_platform_yonetici(
    token: Annotated[str | None, Depends(platform_oauth2)],
    db: Annotated[AsyncSession, Depends(get_session)],
) -> PlatformYonetici:
    """``platform_access`` token'ını doğrular ve platform yöneticisini döndürür."""
    if not token:
        raise KimlikHatasi("Kimlik doğrulaması gerekli")
    try:
        icerik = jwtmod.coz(token, "platform_access")
    except jwtmod.TokenGecersiz as exc:
        raise KimlikHatasi("Geçersiz veya süresi dolmuş token") from exc

    sonuc = await db.execute(
        select(PlatformYonetici).where(PlatformYonetici.id == icerik.kullanici_id)
    )
    yonetici = sonuc.scalar_one_or_none()
    if yonetici is None or not yonetici.aktif:
        raise KimlikHatasi("Platform yöneticisi bulunamadı veya aktif değil")
    return yonetici
