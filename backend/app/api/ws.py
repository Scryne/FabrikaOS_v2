"""Gerçek-zaman WebSocket ucu — tenant-kapsamlı olay akışı (``/api/v1/ws/olaylar``).

Tarayıcı WS el sıkışmasında özel başlık gönderemediği için kimlik **query** ile taşınır:
``?token=<access>&tenant=<slug>``. Kabul öncesi: access token doğrulanır, token'daki
``tenant_slug`` istekteki ``tenant`` ile eşleşmek zorundadır (çapraz-tenant koruması) ve
tenant aktif/abone olmalıdır. Ardından yalnız o tenant'ın kanalına abone olunur.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, WebSocket
from redis.asyncio.client import PubSub
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.websockets import WebSocketDisconnect, WebSocketState

from app.core.db.session import get_session
from app.core.db.tenancy import slug_gecerli_mi, tenant_bul
from app.core.gercekzaman import kanal_adi
from app.core.security import jwt as jwtmod
from app.core.security.redis_istemci import get_redis

logger = logging.getLogger("app.ws")
router = APIRouter()

# Uygulama-tanımlı WS kapatma kodları (4000–4999).
KOD_KIMLIK = 4401  # token yok/geçersiz
KOD_YETKI = 4403  # token tenant'ı ile istek tenant'ı uyuşmuyor (çapraz-tenant)
KOD_TENANT = 4404  # tenant yok/pasif


@router.websocket("/ws/olaylar")
async def olay_akisi(
    websocket: WebSocket,
    db: Annotated[AsyncSession, Depends(get_session)],
    token: Annotated[str | None, Query()] = None,
    tenant: Annotated[str | None, Query()] = None,
) -> None:
    slug = (tenant or "").strip().lower()
    if not token or not slug or not slug_gecerli_mi(slug):
        await websocket.close(code=KOD_KIMLIK)
        return
    try:
        icerik = jwtmod.coz(token, "access")
    except jwtmod.TokenGecersiz:
        await websocket.close(code=KOD_KIMLIK)
        return
    if icerik.tenant_slug != slug:
        await websocket.close(code=KOD_YETKI)
        return
    t = await tenant_bul(db, slug)
    if t is None or not t.aktif or not t.abonelik_gecerli:
        await websocket.close(code=KOD_TENANT)
        return

    await websocket.accept()
    kanal = kanal_adi(slug)
    pubsub = get_redis().pubsub()
    await pubsub.subscribe(kanal)
    try:
        await _kopru(websocket, pubsub)
    except WebSocketDisconnect:
        pass
    finally:
        try:
            await pubsub.unsubscribe(kanal)
            await pubsub.aclose()  # type: ignore[no-untyped-call]
        except Exception:  # noqa: BLE001 — kapanış temizliği hatayı yutar
            logger.debug("pubsub kapanış temizliği başarısız", exc_info=True)


async def _kopru(websocket: WebSocket, pubsub: PubSub) -> None:
    """İki görevi paralel yürütür: pubsub→ws iletimi ve istemci kopuşunun tespiti.
    Biri biterse (kopuş ya da hata) diğeri iptal edilir."""
    ilet = asyncio.create_task(_pubsub_ilet(websocket, pubsub))
    dinle = asyncio.create_task(_kopus_dinle(websocket))
    biten, bekleyen = await asyncio.wait({ilet, dinle}, return_when=asyncio.FIRST_COMPLETED)
    for gorev in bekleyen:
        gorev.cancel()
    for gorev in biten:
        hata = gorev.exception()
        if hata is not None and not isinstance(hata, WebSocketDisconnect):
            raise hata


async def _pubsub_ilet(websocket: WebSocket, pubsub: PubSub) -> None:
    while True:
        # timeout: gerçek Redis'te ~1 sn bloklar; fakeredis hemen None döndürebilir → kısa uyku.
        mesaj = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
        if mesaj is None:
            await asyncio.sleep(0.05)
            continue
        if mesaj.get("type") == "message":
            if websocket.application_state != WebSocketState.CONNECTED:
                return
            await websocket.send_text(mesaj["data"])


async def _kopus_dinle(websocket: WebSocket) -> None:
    # İstemciden veri beklemiyoruz; bu döngü yalnız kopuşu (WebSocketDisconnect) tespit eder.
    while True:
        await websocket.receive_text()
