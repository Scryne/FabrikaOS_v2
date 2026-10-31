"""Prometheus metrikleri (S19, ADR-0040).

SLI'ların kaynağı: istek sayısı (durum koduna göre) ve süre histogramı. Etiketlerde ham yol
değil **rota şablonu** kullanılır (``/api/v1/makineler/{makine_id}``): ham yol her kimlik için
yeni bir zaman serisi açar ve Prometheus'u şişirir. Tenant etiket olarak yazılmaz (yüzlerce
tenant × rota × durum kardinalitesi); tenant kırılımı loglarda ve izlerde.

Süreç-içi tek kayıt defteri (``KAYIT``): API ``/metrics`` ucundan, işçiler kendi portlarından
(``metrik_sunucusu_baslat``) yayınlar.

**Çok işçili uvicorn (S22):** tek süreç ~125 istek/sn'de doyuyor (k6, 2026-11-01); üretimde
``--workers N`` gerekir. O zaman her işçinin sayacı ayrı bellekte durur ve ``/metrics``'i hangi
işçi karşılarsa yalnız onunkini döndürürdü. ``PROMETHEUS_MULTIPROC_DIR`` tanımlıysa
prometheus_client değerleri bu dizindeki dosyalara yazar ve ``metrik_ciktisi`` bütün işçileri
toplar. Dizin her açılışta boşaltılmalıdır (Dockerfile/compose komutu).
"""

from __future__ import annotations

import os
import time
from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    multiprocess,
    start_http_server,
)

from app import __version__

Scope = MutableMapping[str, Any]
Message = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[Message]]
Send = Callable[[Message], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

KAYIT = CollectorRegistry(auto_describe=True)

# Kova sınırları NFR-01'e (p95 < 300 ms) göre: 0,3 s sınırı bir kova kenarıdır, böylece
# "300 ms altındaki istek oranı" histogram_quantile tahmini olmadan doğrudan okunur.
SURE_KOVALARI = (0.01, 0.025, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0)

HTTP_ISTEK = Counter(
    "fabrikaos_http_istekleri",
    "Tamamlanan HTTP istekleri (yöntem, rota şablonu, durum kodu).",
    ["yontem", "rota", "durum"],
    registry=KAYIT,
)
HTTP_SURE = Histogram(
    "fabrikaos_http_istek_suresi_saniye",
    "HTTP istek süresi (yanıtın son baytına kadar).",
    ["yontem", "rota"],
    buckets=SURE_KOVALARI,
    registry=KAYIT,
)
HTTP_SUREN = Gauge(
    "fabrikaos_http_suren_istekler",
    "Şu anda işlenen HTTP istekleri.",
    registry=KAYIT,
    multiprocess_mode="livesum",  # çok işçide yaşayan süreçlerin toplamı
)
SURUM = Gauge(
    "fabrikaos_surum_bilgisi",
    "Çalışan sürüm (değer her zaman 1).",
    ["surum"],
    registry=KAYIT,
    multiprocess_mode="max",
)
SURUM.labels(surum=__version__).set(1)

# İşçi metrikleri (ingestion, bildirim, webhook relay): aynı defter, ayrı süreç.
ISCI_MESAJ = Counter(
    "fabrikaos_isci_mesajlari",
    "İşçinin işlediği mesaj/olaylar (işçi, sonuç: islendi | dusuruldu | hata).",
    ["isci", "sonuc"],
    registry=KAYIT,
)
ISCI_SON_BASARI = Gauge(
    "fabrikaos_isci_son_basari_zamani",
    "İşçinin son başarılı işleminin Unix zamanı (durgunluk alarmı için).",
    ["isci"],
    registry=KAYIT,
    multiprocess_mode="max",
)

ESLESMEYEN = "eslesmeyen"
_HARIC_YOLLAR = frozenset({"/metrics"})


def rota_sablonu(scope: Scope) -> str:
    """Yönlendiricinin eşleştirdiği rota şablonu; eşleşme yoksa sabit etiket (404 taraması)."""
    rota = scope.get("route")
    sablon = getattr(rota, "path", None)
    return sablon if isinstance(sablon, str) else ESLESMEYEN


class MetrikMiddleware:
    """İstek sayısı/süresi (saf ASGI). Hata katmanının DIŞINDA durur: üretilen 500'ler sayılır."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in _HARIC_YOLLAR:
            await self.app(scope, receive, send)
            return

        durum = 500  # yanıt başlamadan istisna kaçarsa sunucu hatası sayılır
        baslangic = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal durum
            if message["type"] == "http.response.start":
                durum = int(message["status"])
            await send(message)

        HTTP_SUREN.inc()
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            HTTP_SUREN.dec()
            yontem = str(scope.get("method", "GET"))
            rota = rota_sablonu(scope)
            HTTP_ISTEK.labels(yontem=yontem, rota=rota, durum=str(durum)).inc()
            HTTP_SURE.labels(yontem=yontem, rota=rota).observe(time.perf_counter() - baslangic)


def isci_sonuc(isci: str, sonuc: str) -> None:
    """İşçi döngüsünden tek satırlık sayaç; ``islendi`` son başarı zamanını da günceller."""
    ISCI_MESAJ.labels(isci=isci, sonuc=sonuc).inc()
    if sonuc == "islendi":
        ISCI_SON_BASARI.labels(isci=isci).set(time.time())


def metrik_ciktisi() -> tuple[bytes, str]:
    """Prometheus metin biçimi; çok süreç modunda bütün işçilerin toplamı."""
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        toplayici = CollectorRegistry()
        multiprocess.MultiProcessCollector(toplayici)  # type: ignore[no-untyped-call]
        return generate_latest(toplayici), CONTENT_TYPE_LATEST
    return generate_latest(KAYIT), CONTENT_TYPE_LATEST


def metrik_sunucusu_baslat(port: int) -> None:
    """İşçi süreçleri için ayrı /metrics HTTP sunucusu (0 = kapalı)."""
    if port > 0:
        start_http_server(port, registry=KAYIT)
