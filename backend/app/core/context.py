"""İstek-kapsamlı bağlam değişkenleri (contextvars).

Loglama korelasyonu için kullanılır: her log satırına `request_id` ve `tenant`
otomatik eklenir. Değerler `RequestContextMiddleware` tarafından her istekte set edilir.
"""

from __future__ import annotations

from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
tenant_slug_ctx: ContextVar[str] = ContextVar("tenant_slug", default="-")
