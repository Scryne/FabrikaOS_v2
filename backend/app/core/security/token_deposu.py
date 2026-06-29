"""Refresh token iptal listesi (denylist) — Redis.

Rotasyon/çıkışta refresh ``jti`` iptal listesine eklenir; süresi token'ın kalan ömrü
kadardır. Bir refresh token kullanılmadan önce iptalli olup olmadığı kontrol edilir.
"""

from __future__ import annotations

from app.core.security.redis_istemci import get_redis

_ONEK = "iptal:refresh:"


async def refresh_iptal_et(jti: str, ttl_sn: int) -> None:
    """``jti``'yi iptal listesine ekler (TTL = kalan ömür, en az 1 sn)."""
    await get_redis().set(_ONEK + jti, "1", ex=max(ttl_sn, 1))


async def refresh_iptalli_mi(jti: str) -> bool:
    """``jti`` iptal listesinde mi?"""
    return bool(await get_redis().exists(_ONEK + jti))
