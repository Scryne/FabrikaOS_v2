"""Yapılandırılmış (JSON) loglama.

Her log satırına istek bağlamından `request_id` ve `tenant` eklenir (korelasyon).
Ek bağımlılık gerektirmeyen, stdlib tabanlı bir JSON formatlayıcı kullanılır.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.core.context import request_id_ctx, tenant_slug_ctx


class ContextFilter(logging.Filter):
    """Aktif istek bağlamını her log kaydına enjekte eder."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        record.tenant_slug = tenant_slug_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "zaman": datetime.now(UTC).isoformat(),
            "seviye": record.levelname,
            "logger": record.name,
            "mesaj": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "tenant": getattr(record, "tenant_slug", "-"),
        }
        if record.exc_info:
            payload["hata"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def yapilandir_loglama(level: str = "INFO") -> None:
    """Kök logger'ı JSON formatı + bağlam filtresiyle kurar."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(ContextFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    # Uvicorn erişim/hata loglarını da kök handler'a yönlendir.
    for adi in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(adi)
        lg.handlers.clear()
        lg.propagate = True
