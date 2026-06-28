"""İstek bağlamı middleware'i (saf ASGI).

- Her isteğe bir `request_id` atar (gelen `X-Request-Id` varsa korur) ve yanıta ekler.
- Tenant slug'ını (subdomain veya `X-Tenant`) yalnızca LOGLAMA bağlamına yazar.

NOT: Tenant'ın geçerliliği/aboneliği ve cross-tenant koruması S2'de `tenant_cozumle`
dependency'sinde DOĞRULANIR. Buradaki yakalama yalnızca log korelasyonu içindir.

Saf ASGI middleware kullanılır; böylece contextvar değerleri endpoint task'ına
güvenilir biçimde aktarılır (BaseHTTPMiddleware'in task-sınırı tuzağı yaşanmaz).
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from app.core.context import request_id_ctx, tenant_slug_ctx

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


def _tenant_slug(headers: dict[str, str]) -> str:
    x_tenant = headers.get("x-tenant")
    if x_tenant:
        return x_tenant.strip().lower()
    host = headers.get("host", "").split(":")[0]
    parcalar = host.split(".")
    # ornek: fabrika-a.fabrikaos.localhost -> "fabrika-a"
    if len(parcalar) >= 3:
        return parcalar[0].lower()
    return "-"


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            k.decode("latin1").lower(): v.decode("latin1") for k, v in scope.get("headers", [])
        }
        request_id = headers.get("x-request-id") or uuid.uuid4().hex

        request_id_ctx.set(request_id)
        tenant_slug_ctx.set(_tenant_slug(headers))

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                yeni = list(message.get("headers", []))
                yeni.append((b"x-request-id", request_id.encode("latin1")))
                message["headers"] = yeni
            await send(message)

        await self.app(scope, receive, send_wrapper)
