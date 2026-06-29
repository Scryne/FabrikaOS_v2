"""Basit sabit-pencere (fixed-window) rate limit — Redis.

Anahtar başına pencere içindeki istek sayısını sayar. İlk istekte pencere TTL'i ayarlanır.
Brute-force'a karşı özellikle ``/kimlik/token`` (giriş) ucunda kullanılır.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.core.security.redis_istemci import get_redis

_ONEK = "rl:"


@dataclass(frozen=True, slots=True)
class RateLimitSonuc:
    izinli: bool
    kalan: int
    limit: int


async def rate_limit_kontrol(
    anahtar: str, *, limit: int | None = None, pencere_sn: int | None = None
) -> RateLimitSonuc:
    """``anahtar`` için bir istek sayar; limiti aşıyorsa ``izinli=False`` döner."""
    ayar = get_settings()
    limit = ayar.rate_limit_istek if limit is None else limit
    pencere_sn = ayar.rate_limit_pencere_sn if pencere_sn is None else pencere_sn

    r = get_redis()
    k = _ONEK + anahtar
    sayi = await r.incr(k)
    if sayi == 1:
        await r.expire(k, pencere_sn)
    kalan = max(limit - int(sayi), 0)
    return RateLimitSonuc(izinli=int(sayi) <= limit, kalan=kalan, limit=limit)
