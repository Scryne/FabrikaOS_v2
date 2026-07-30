"""JWT üretimi ve çözümlemesi (OAuth2 Bearer).

İki tür token:
- **access** — kısa ömürlü (varsayılan 15 dk); ``eposta`` claim'i taşır.
- **refresh** — uzun ömürlü (varsayılan 7 gün); rotasyonludur (Redis iptal listesi ile).

Her token bir ``jti`` (benzersiz kimlik) taşır; iptal/rotasyon bu kimlik üzerinden yapılır.
``tenant_slug`` claim'i, isteğin subdomain'i ile eşleşmek zorundadır (cross-tenant koruması).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import get_settings


class TokenGecersiz(Exception):
    """JWT çözümlenemedi, süresi doldu veya tipi beklenenden farklı."""


@dataclass(frozen=True, slots=True)
class TokenIcerigi:
    kullanici_id: int
    tenant_slug: str
    tip: str
    jti: str
    exp: int
    eposta: str | None = None
    # 2FA geçici token'ı kurulum amaçlı mı (zorunlu-2FA ilk girişi; S23).
    kurulum: bool = False


def _kodla(claims: dict[str, Any], omur: timedelta) -> tuple[str, str]:
    ayar = get_settings()
    simdi = datetime.now(UTC)
    jti = uuid.uuid4().hex
    govde = {
        **claims,
        "jti": jti,
        "iat": int(simdi.timestamp()),
        "exp": int((simdi + omur).timestamp()),
    }
    token = jwt.encode(govde, ayar.secret_key, algorithm=ayar.jwt_algoritma)
    return token, jti


def access_uret(kullanici_id: int, tenant_slug: str, eposta: str) -> tuple[str, str]:
    """Access token üretir → (token, jti)."""
    ayar = get_settings()
    return _kodla(
        {
            "sub": str(kullanici_id),
            "tenant_slug": tenant_slug,
            "eposta": eposta,
            "tip": "access",
        },
        timedelta(minutes=ayar.access_token_dakika),
    )


def refresh_uret(kullanici_id: int, tenant_slug: str) -> tuple[str, str]:
    """Refresh token üretir → (token, jti)."""
    ayar = get_settings()
    return _kodla(
        {"sub": str(kullanici_id), "tenant_slug": tenant_slug, "tip": "refresh"},
        timedelta(days=ayar.refresh_token_gun),
    )


def iki_asama_uret(
    kullanici_id: int, tenant_slug: str, *, kurulum: bool = False
) -> tuple[str, str]:
    """2FA ara token'ı üretir (S23) → (token, jti). Kısa ömürlü (5 dk).

    Parola doğrulandı ama ikinci aşama tamamlanmadı: bu token yalnız
    ``/kimlik/2fa-dogrula`` (ve ``kurulum=True`` iken 2FA kurulum uçlarında) geçerlidir —
    ayrı ``tip`` değeri onu access olarak kullanılamaz kılar (yapısal ayrım).
    """
    return _kodla(
        {
            "sub": str(kullanici_id),
            "tenant_slug": tenant_slug,
            "tip": "2fa",
            "kurulum": kurulum,
        },
        timedelta(minutes=5),
    )


# --- Platform (control-plane) düzlemi — S17 / ADR-0019 ---
# Ayrı ``tip`` değerleri düzlemleri YAPISAL olarak ayırır: tenant token'ı platform
# ucunda, platform token'ı tenant ucunda tip kontrolünden geçemez (401).
# ``tenant_slug`` claim'i platform token'larında inert bir sabittir.
PLATFORM_SLUG_SABITI = "platform"


def platform_access_uret(yonetici_id: int, eposta: str) -> tuple[str, str]:
    """Platform yöneticisi access token'ı üretir → (token, jti)."""
    ayar = get_settings()
    return _kodla(
        {
            "sub": str(yonetici_id),
            "tenant_slug": PLATFORM_SLUG_SABITI,
            "eposta": eposta,
            "tip": "platform_access",
        },
        timedelta(minutes=ayar.access_token_dakika),
    )


def platform_refresh_uret(yonetici_id: int) -> tuple[str, str]:
    """Platform yöneticisi refresh token'ı üretir → (token, jti)."""
    ayar = get_settings()
    return _kodla(
        {"sub": str(yonetici_id), "tenant_slug": PLATFORM_SLUG_SABITI, "tip": "platform_refresh"},
        timedelta(days=ayar.refresh_token_gun),
    )


def coz(token: str, beklenen_tip: str) -> TokenIcerigi:
    """Token'ı doğrular ve içeriğini döndürür; geçersizse ``TokenGecersiz``."""
    ayar = get_settings()
    try:
        govde = jwt.decode(token, ayar.secret_key, algorithms=[ayar.jwt_algoritma])
    except jwt.PyJWTError as exc:
        raise TokenGecersiz(str(exc)) from exc
    if govde.get("tip") != beklenen_tip:
        raise TokenGecersiz(f"Beklenen token tipi {beklenen_tip!r}, gelen {govde.get('tip')!r}")
    try:
        return TokenIcerigi(
            kullanici_id=int(govde["sub"]),
            tenant_slug=str(govde["tenant_slug"]),
            tip=str(govde["tip"]),
            jti=str(govde["jti"]),
            exp=int(govde["exp"]),
            eposta=govde.get("eposta"),
            kurulum=bool(govde.get("kurulum", False)),
        )
    except (KeyError, ValueError) as exc:
        raise TokenGecersiz(f"Eksik/bozuk claim: {exc}") from exc
