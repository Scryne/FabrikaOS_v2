"""Sentry hata izleme (S19, ADR-0040).

Kabul: "hata Sentry'de tenant/istek bağlamıyla görünür". Her olaya ``tenant`` ve
``request_id`` etiketi eklenir; log satırındaki ``request_id`` ile aynı değer olduğu için
Sentry'deki bir hatadan o isteğin tüm loglarına gidilir.

Kişisel veri gönderilmez (``send_default_pii=False``); ayrıca istek başlıklarındaki kimlik
bilgisi ve sorgu dizesindeki token'lar olay gönderilmeden temizlenir (KVKK, NFR-06). Yığın
çerçevelerinin yerel değişkenleri de gönderilmez: ASGI ``scope`` ham ``Authorization``
başlığını taşır, servis katmanındaki yereller parola/kişisel veri taşıyabilir (testle
yakalandı, 2026-11-01).
DSN boşsa hiçbir şey kurulmaz ve ``hata_bildir`` sessizce no-op olur.
"""

from __future__ import annotations

from typing import Any

import sentry_sdk
from sentry_sdk.transport import Transport

from app import __version__
from app.core.config import Settings
from app.core.context import cozulmus_tenant_ctx, request_id_ctx, tenant_slug_ctx
from app.core.logging import gizli_maskele

_GIZLI_BASLIKLAR = frozenset(
    {"authorization", "cookie", "set-cookie", "x-api-key", "x-api-anahtari"}
)
_TEMIZ = "[gizli]"


def _baglam_ekle(event: Any, hint: Any) -> Any:
    """Olaya tenant/request_id etiketi ekler, gizli başlık ve token'ları temizler."""
    etiketler = event.setdefault("tags", {})
    # Doğrulanmış tenant varsa o; yoksa ham başlık/alt alan adı (yalnız korelasyon için).
    etiketler["tenant"] = cozulmus_tenant_ctx.get() or tenant_slug_ctx.get()
    etiketler["request_id"] = request_id_ctx.get()

    istek = event.get("request")
    if isinstance(istek, dict):
        basliklar = istek.get("headers")
        if isinstance(basliklar, dict):
            for ad in list(basliklar):
                if ad.lower() in _GIZLI_BASLIKLAR:
                    basliklar[ad] = _TEMIZ
        if isinstance(istek.get("query_string"), str):
            istek["query_string"] = gizli_maskele("?" + istek["query_string"])[1:]
        if isinstance(istek.get("url"), str):
            istek["url"] = gizli_maskele(istek["url"])
        istek.pop("cookies", None)
        istek.pop("data", None)  # gövde (parola, kişisel veri) hiç gönderilmez
    return event


def hata_izleme_kur(
    ayar: Settings, *, transport: type[Transport] | Transport | None = None
) -> bool:
    """DSN tanımlıysa Sentry'yi kurar; kurulduysa True döner."""
    if not ayar.sentry_dsn:
        return False
    sentry_sdk.init(
        dsn=ayar.sentry_dsn,
        environment=ayar.sentry_ortam or ayar.app_env,
        release=f"fabrikaos@{__version__}",
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        traces_sample_rate=ayar.sentry_iz_orani,
        before_send=_baglam_ekle,
        transport=transport,
    )
    return True


def hata_bildir(exc: BaseException) -> None:
    """Yakalanmış istisnayı Sentry'ye iletir (Sentry kurulu değilse no-op)."""
    sentry_sdk.capture_exception(exc)
