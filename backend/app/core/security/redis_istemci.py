"""Tekil async Redis istemcisi (refresh iptal listesi + rate limit için).

Tembel oluşturulur; testler ``redis_ayarla`` ile fakeredis enjekte edebilir.
"""

from __future__ import annotations

from redis.asyncio import Redis
from redis.asyncio import from_url as _from_url

from app.core.config import get_settings

_redis: Redis | None = None


def get_redis() -> Redis:
    """Süreç-genelinde tekil Redis istemcisi (string modunda)."""
    global _redis
    if _redis is None:
        _redis = _from_url(get_settings().redis_url, encoding="utf-8", decode_responses=True)
    return _redis


def redis_ayarla(client: Redis | None) -> None:
    """İstemciyi override eder (testlerde fakeredis için); ``None`` sıfırlar."""
    global _redis
    _redis = client
