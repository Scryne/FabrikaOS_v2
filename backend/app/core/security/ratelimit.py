"""Basit sabit-pencere (fixed-window) rate limit — Redis.

Anahtar başına pencere içindeki istek sayısını sayar. İlk istekte pencere TTL'i ayarlanır.
Brute-force'a karşı özellikle ``/kimlik/token`` (giriş) ucunda kullanılır.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from app.core.config import get_settings
from app.core.security.redis_istemci import get_redis

_ONEK = "rl:"


@dataclass(frozen=True, slots=True)
class RateLimitSonuc:
    izinli: bool
    kalan: int
    limit: int


# Redis kesintisinde süreç içi yedek (S28, ADR-0047): işçi başına ayrı sayar, yani N işçide sınır
# en kötü N katına çıkar; kesinti süresince kabul edilen gevşeme budur. Redis dönünce kullanılmaz.
logger = logging.getLogger("app.security.ratelimit")

_YEDEK: dict[str, tuple[float, int]] = {}


def _yedek_say(anahtar: str, pencere_sn: int) -> int:
    simdi = time.monotonic()
    bas, sayi = _YEDEK.get(anahtar, (simdi, 0))
    if simdi - bas >= pencere_sn:
        bas, sayi = simdi, 0
    _YEDEK[anahtar] = (bas, sayi + 1)
    if len(_YEDEK) > 10_000:  # bellek sınırı: en eski pencereler atılır
        for eski in sorted(_YEDEK, key=lambda x: _YEDEK[x][0])[:5_000]:
            _YEDEK.pop(eski, None)
    return sayi + 1


async def rate_limit_kontrol(
    anahtar: str, *, limit: int | None = None, pencere_sn: int | None = None
) -> RateLimitSonuc:
    """``anahtar`` için bir istek sayar; limiti aşıyorsa ``izinli=False`` döner."""
    ayar = get_settings()
    limit = ayar.rate_limit_istek if limit is None else limit
    pencere_sn = ayar.rate_limit_pencere_sn if pencere_sn is None else pencere_sn

    k = _ONEK + anahtar
    try:
        r = get_redis()
        sayi = await r.incr(k)
        if sayi == 1:
            await r.expire(k, pencere_sn)
    except Exception:  # noqa: BLE001 — Redis kesintisi girişi kilitlememeli, korumayı da kaldırmamalı
        logger.warning("rate limit: Redis yok, süreç içi yedek sayaç kullanılıyor (%s)", anahtar)
        sayi = _yedek_say(k, pencere_sn)
    kalan = max(limit - int(sayi), 0)
    return RateLimitSonuc(izinli=int(sayi) <= limit, kalan=kalan, limit=limit)
