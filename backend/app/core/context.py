"""İstek-kapsamlı bağlam değişkenleri (contextvars).

Loglama korelasyonu için kullanılır: her log satırına `request_id` ve `tenant`
otomatik eklenir. Değerler `RequestContextMiddleware` tarafından her istekte set edilir.
"""

from __future__ import annotations

from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
tenant_slug_ctx: ContextVar[str] = ContextVar("tenant_slug", default="-")
# İstemci IP'si (denetim izinde ``ip_adresi`` olarak kullanılır). Ters proxy arkasında
# uvicorn ``--proxy-headers`` ile gerçek istemciyi yansıtır; aksi hâlde doğrudan eş IP'sidir.
istemci_ip_ctx: ContextVar[str | None] = ContextVar("istemci_ip", default=None)
