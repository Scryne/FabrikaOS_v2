"""Gerçek-zaman yayın katmanı — Redis pub/sub, tenant-kapsamlı kanallar.

Kanal adı ``tenant:<slug>:olaylar`` olduğundan **izolasyon yapısaldır**: bir tenant'ın
WebSocket'i yalnız kendi kanalına abone olur, başka tenant'ın olayını asla almaz (R3).

Yayın **best-effort**'tur: Redis erişilemezse istek bozulmaz — canlı UI sinyali gözden
kaçsa bile istemci periyodik/olay-tetikli refetch ile yakalar. Dayanıklı domain olayları
(webhook teslimatı) ayrıca transactional outbox'ta (``core/olaylar.py``) tutulur (ADR-0009).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.db.tenancy import slug_gecerli_mi
from app.core.security.redis_istemci import get_redis

logger = logging.getLogger("app.gercekzaman")


def kanal_adi(slug: str) -> str:
    """``slug`` → ``tenant:<slug>:olaylar`` pub/sub kanalı. Geçersiz slug'da ``ValueError``."""
    if not slug_gecerli_mi(slug):
        raise ValueError(f"Geçersiz tenant slug: {slug!r}")
    return f"tenant:{slug}:olaylar"


async def yayinla(slug: str, olay: dict[str, Any]) -> None:
    """Olayı tenant'ın gerçek-zaman kanalına yayınlar (best-effort; isteği bozmaz)."""
    try:
        kanal = kanal_adi(slug)
    except ValueError:
        logger.warning("geçersiz slug ile yayın atlandı: %r", slug)
        return
    try:
        redis = get_redis()
        await redis.publish(kanal, json.dumps(olay, ensure_ascii=False))
    except Exception:  # noqa: BLE001 — yayın asla isteği düşürmez
        logger.warning("gerçek-zaman yayını başarısız (kanal=%s)", kanal, exc_info=True)
