"""OpenTelemetry dağıtık izleme (S19, ADR-0040).

``OTEL_ENDPOINT`` tanımlıysa istekler (FastAPI) ve SQL sorguları (SQLAlchemy) span olarak
OTLP/HTTP toplayıcısına gider. Sunucu span'ine ``fabrikaos.tenant`` ve
``fabrikaos.request_id`` öznitelikleri ``RequestContextMiddleware`` tarafından yazılır;
JSON log satırına da ``trace_id`` eklenir — log, iz ve Sentry olayı aynı istekte buluşur.

Kapalıyken OpenTelemetry API'si no-op sağlayıcıyla çalışır; ek maliyet yoktur.
"""

from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter
from sqlalchemy.ext.asyncio import AsyncEngine

from app import __version__
from app.core.config import Settings

# Sağlık ve metrik kazıması iz üretmez (her 15 sn'de bir gürültü span'i olurdu).
_HARIC_URL = "saglik,metrics"


def izleme_saglayici(
    ayar: Settings, *, disaridan: SpanExporter | None = None
) -> TracerProvider | None:
    """Ayar ya da enjekte edilen dışa aktarıcıyla sağlayıcı kurar; kapalıysa None."""
    if disaridan is None and not ayar.otel_endpoint:
        return None
    saglayici = TracerProvider(
        resource=Resource.create(
            {
                "service.name": ayar.otel_servis_adi,
                "service.version": __version__,
                "deployment.environment": ayar.app_env,
            }
        )
    )
    if disaridan is not None:
        saglayici.add_span_processor(SimpleSpanProcessor(disaridan))
    else:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        uc = ayar.otel_endpoint.rstrip("/") + "/v1/traces"
        saglayici.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=uc)))
    return saglayici


def izleme_kur(
    app: FastAPI,
    engine: AsyncEngine | None,
    ayar: Settings,
    *,
    disaridan: SpanExporter | None = None,
) -> TracerProvider | None:
    """Uygulamayı ve (verildiyse) DB motorunu enstrümante eder."""
    saglayici = izleme_saglayici(ayar, disaridan=disaridan)
    if saglayici is None:
        return None
    if disaridan is None:
        # Küresel sağlayıcı yalnız gerçek kurulumda (süreçte bir kez) ayarlanır; testler
        # kendi sağlayıcılarını doğrudan geçirir.
        trace.set_tracer_provider(saglayici)
    FastAPIInstrumentor.instrument_app(app, tracer_provider=saglayici, excluded_urls=_HARIC_URL)
    if engine is not None:
        # Enstrümantasyon paketi "sqlalchemy < 2.1" bildiriyor; kurulu 2.1 ile bağımlılık
        # denetimi sessizce hiçbir şey yapmıyordu (canlı denemede yakalandı, 2026-10-31).
        # Kullandığı motor olay kancaları 2.1'de değişmedi; SQL span'leri test ve canlı
        # Jaeger turuyla doğrulandı.
        SQLAlchemyInstrumentor().instrument(
            engine=engine.sync_engine, tracer_provider=saglayici, skip_dep_check=True
        )
    return saglayici


def iz_kimligi() -> str | None:
    """Etkin span'in trace_id'si (32 hex); span yoksa None."""
    baglam = trace.get_current_span().get_span_context()
    return format(baglam.trace_id, "032x") if baglam.is_valid else None


def span_baglami_yaz(tenant: str, request_id: str) -> None:
    """Etkin (sunucu) span'ine tenant ve istek kimliğini yazar; span yoksa no-op."""
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("fabrikaos.tenant", tenant)
        span.set_attribute("fabrikaos.request_id", request_id)
