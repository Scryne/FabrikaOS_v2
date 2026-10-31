"""S19 gözlemlenebilirlik: hazırlık yoklaması, Prometheus metrikleri, Sentry bağlamı, OTel izi.

Kabul (yol haritası S19): hata Sentry'de tenant/istek bağlamıyla görünür; SLI panolarının
kaynağı olan metrikler rota şablonuyla üretilir; iz ile log aynı ``trace_id``'yi taşır.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest
import sentry_sdk
from fastapi import FastAPI
from fastapi.testclient import TestClient
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

from app.api import saglik
from app.core.config import Settings, get_settings
from app.core.izleme import iz_kimligi, izleme_kur
from app.core.logging import ContextFilter, JsonFormatter
from app.core.metrikler import KAYIT, isci_sonuc
from app.main import create_app


def _uygulama() -> FastAPI:
    get_settings.cache_clear()
    app = create_app()

    @app.get("/_oge/{oge_id}")
    async def _oge(oge_id: int) -> dict[str, Any]:
        return {"oge": oge_id, "trace_id": iz_kimligi()}

    @app.get("/_patla")
    async def _patla() -> None:
        raise RuntimeError("altyapi yok")

    return app


def _ornek(ad: str, **etiket: str) -> float:
    return KAYIT.get_sample_value(ad, etiket) or 0.0


# --- Hazırlık (readiness) ---------------------------------------------------------------


async def _tamam() -> None:
    return None


async def _patlayan() -> None:
    raise ConnectionRefusedError("db kapalı")


async def _asili() -> None:
    await asyncio.sleep(10)


@pytest.mark.parametrize(
    ("db", "redis", "kod", "beklenen"),
    [
        (_tamam, _tamam, 200, {"veritabani": "ayakta", "redis": "ayakta"}),
        (_patlayan, _tamam, 503, {"veritabani": "hata", "redis": "ayakta"}),
        (_tamam, _asili, 503, {"veritabani": "ayakta", "redis": "zaman_asimi"}),
    ],
)
def test_hazirlik_bagimliliklari_yoklar(monkeypatch, db, redis, kod, beklenen) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(saglik, "_db_yokla", db)
    monkeypatch.setattr(saglik, "_redis_yokla", redis)
    monkeypatch.setattr(saglik, "HAZIRLIK_ZAMAN_ASIMI_SN", 0.1)
    r = TestClient(_uygulama()).get("/saglik/hazir")
    assert r.status_code == kod
    veri = r.json()["data"]
    assert veri["hazir"] is (kod == 200)
    assert r.json()["success"] is (kod == 200)
    assert {k["ad"]: k["durum"] for k in veri["kontroller"]} == beklenen
    # Hata türü yanıtta, ayrıntılı mesaj (bağlantı dizesi vb.) yok.
    assert "db kapalı" not in r.text


# --- Prometheus metrikleri --------------------------------------------------------------


def test_metrik_rota_sablonu_ve_durum_kodu() -> None:
    istemci = TestClient(_uygulama(), raise_server_exceptions=False)
    once = {
        "sablon": _ornek(
            "fabrikaos_http_istekleri_total", yontem="GET", rota="/_oge/{oge_id}", durum="200"
        ),
        "eslesmeyen": _ornek(
            "fabrikaos_http_istekleri_total", yontem="GET", rota="eslesmeyen", durum="404"
        ),
        "patla": _ornek(
            "fabrikaos_http_istekleri_total", yontem="GET", rota="/_patla", durum="500"
        ),
        "sure": _ornek(
            "fabrikaos_http_istek_suresi_saniye_count", yontem="GET", rota="/_oge/{oge_id}"
        ),
    }
    for i in (1, 2, 3):
        assert istemci.get(f"/_oge/{i}").status_code == 200
    assert istemci.get("/boyle-bir-uc-yok/42").status_code == 404
    assert istemci.get("/_patla").status_code == 500

    # Üç farklı kimlik tek zaman serisine düşer (ham yol değil şablon).
    assert (
        _ornek("fabrikaos_http_istekleri_total", yontem="GET", rota="/_oge/{oge_id}", durum="200")
        == once["sablon"] + 3
    )
    assert (
        _ornek("fabrikaos_http_istek_suresi_saniye_count", yontem="GET", rota="/_oge/{oge_id}")
        == once["sure"] + 3
    )
    assert (
        _ornek("fabrikaos_http_istekleri_total", yontem="GET", rota="eslesmeyen", durum="404")
        == once["eslesmeyen"] + 1
    )
    # Hata katmanının ürettiği 500 de SLI'ya sayılır (metrik katmanı onun dışında).
    assert (
        _ornek("fabrikaos_http_istekleri_total", yontem="GET", rota="/_patla", durum="500")
        == once["patla"] + 1
    )

    govde = istemci.get("/metrics").text
    assert 'fabrikaos_http_istekleri_total{durum="200",rota="/_oge/{oge_id}",yontem="GET"}' in govde
    assert "/_oge/1" not in govde
    assert "fabrikaos_surum_bilgisi" in govde
    # /metrics kazıması kendini saymaz.
    assert 'rota="/metrics"' not in govde


def test_metrik_ucu_token_ister(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("METRIK_TOKEN", "kazima-gizli")
    istemci = TestClient(_uygulama())
    try:
        assert istemci.get("/metrics").status_code == 401
        assert (
            istemci.get("/metrics", headers={"Authorization": "Bearer yanlis"}).status_code == 401
        )
        r = istemci.get("/metrics", headers={"Authorization": "Bearer kazima-gizli"})
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/plain")
    finally:
        get_settings.cache_clear()


def test_isci_sayaci_ve_son_basari_zamani() -> None:
    once = _ornek("fabrikaos_isci_mesajlari_total", isci="test_isci", sonuc="islendi")
    isci_sonuc("test_isci", "islendi")
    isci_sonuc("test_isci", "hata")
    assert _ornek("fabrikaos_isci_mesajlari_total", isci="test_isci", sonuc="islendi") == once + 1
    assert _ornek("fabrikaos_isci_mesajlari_total", isci="test_isci", sonuc="hata") >= 1
    assert _ornek("fabrikaos_isci_son_basari_zamani", isci="test_isci") > 1_700_000_000


async def test_ingestion_gecersiz_mesaj_dusuruldu_sayilir() -> None:
    from app.ingestion.worker import mesaj_ele

    once = _ornek("fabrikaos_isci_mesajlari_total", isci="ingestion", sonuc="dusuruldu")
    await mesaj_ele(None, "yanlis/topic", b"{}")  # type: ignore[arg-type] — çözümleme DB'den önce düşer
    assert _ornek("fabrikaos_isci_mesajlari_total", isci="ingestion", sonuc="dusuruldu") == once + 1


# --- Sentry -----------------------------------------------------------------------------


class _Yakalayici(Transport):
    def __init__(self) -> None:
        super().__init__()
        self.olaylar: list[dict[str, Any]] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        olay = envelope.get_event()
        if olay is not None:
            self.olaylar.append(olay)


@pytest.fixture
def sentry_yakala(monkeypatch) -> Iterator[_Yakalayici]:  # type: ignore[no-untyped-def]
    yakalayici = _Yakalayici()
    monkeypatch.setenv("SENTRY_DSN", "https://acik@o0.ingest.sentry.io/1")
    monkeypatch.setattr("app.main.hata_izleme_kur", _sabit_transport(yakalayici))
    try:
        yield yakalayici
    finally:
        sentry_sdk.get_client().close(timeout=0)
        # sentry_sdk.init() DSN verilmezse SENTRY_DSN ortam değişkenini okur: önce silinmeli,
        # yoksa sahte DSN'li gerçek bir istemci kurulur ve sonraki testlerin olayları dışarı
        # gönderilmeye çalışılır.
        monkeypatch.delenv("SENTRY_DSN", raising=False)
        sentry_sdk.init()
        assert sentry_sdk.get_client().transport is None
        get_settings.cache_clear()


def _sabit_transport(yakalayici: _Yakalayici):  # type: ignore[no-untyped-def]
    from app.core.hata_izleme import hata_izleme_kur

    def kur(ayar: Settings) -> bool:
        return hata_izleme_kur(ayar, transport=yakalayici)

    return kur


def test_sentry_olayi_tenant_ve_istek_baglamini_tasir(sentry_yakala: _Yakalayici) -> None:
    istemci = TestClient(_uygulama(), raise_server_exceptions=False)
    r = istemci.get(
        "/_patla?token=gizli-jwt",
        headers={
            "X-Tenant": "fabrika-a",
            "X-Request-Id": "istek-77",
            "Authorization": "Bearer gizli-jwt",
        },
    )
    assert r.status_code == 500
    sentry_sdk.flush()
    assert len(sentry_yakala.olaylar) == 1, "istisna tam bir kez raporlanmalı"
    olay = sentry_yakala.olaylar[0]
    assert olay["tags"]["tenant"] == "fabrika-a"
    assert olay["tags"]["request_id"] == "istek-77"
    assert olay["exception"]["values"][-1]["value"] == "altyapi yok"
    # Kimlik bilgisi ve token olaydan temizlenmiş olmalı.
    assert "gizli-jwt" not in json.dumps(olay, ensure_ascii=False, default=str)


def test_sentry_dsn_yoksa_kurulmaz() -> None:
    from app.core.hata_izleme import hata_izleme_kur

    assert hata_izleme_kur(Settings(sentry_dsn="")) is False


# --- OpenTelemetry ----------------------------------------------------------------------


def test_otel_sunucu_spani_tenant_ve_istek_kimligi_tasir() -> None:
    disari = InMemorySpanExporter()
    app = _uygulama()
    saglayici = izleme_kur(app, None, Settings(), disaridan=disari)
    assert saglayici is not None
    istemci = TestClient(app)
    r = istemci.get("/_oge/7", headers={"X-Tenant": "fabrika-b", "X-Request-Id": "istek-88"})
    assert r.status_code == 200
    assert istemci.get("/saglik").status_code == 200  # hariç tutulan yol iz üretmez

    spanlar = disari.get_finished_spans()
    sunucu = [s for s in spanlar if (s.attributes or {}).get("fabrikaos.request_id") == "istek-88"]
    assert len(sunucu) == 1
    assert sunucu[0].attributes["fabrikaos.tenant"] == "fabrika-b"  # type: ignore[index]
    # Uygulama kodunun gördüğü trace_id, dışa aktarılan span'inkiyle aynı.
    assert r.json()["trace_id"] == format(sunucu[0].context.trace_id, "032x")
    assert not any("/saglik" in s.name for s in spanlar)


def test_json_log_satiri_trace_id_tasir() -> None:
    saglayici = TracerProvider()
    disari = InMemorySpanExporter()
    saglayici.add_span_processor(SimpleSpanProcessor(disari))
    kayit = logging.LogRecord("app", logging.INFO, __file__, 1, "olay", None, None)
    ContextFilter().filter(kayit)
    assert "trace_id" not in json.loads(JsonFormatter().format(kayit))
    with saglayici.get_tracer("test").start_as_current_span("is") as span:
        satir = json.loads(JsonFormatter().format(kayit))
    assert satir["trace_id"] == format(span.get_span_context().trace_id, "032x")


async def test_otel_sql_spani_uretilir(test_db: str) -> None:
    """SQLAlchemy 2.1 ile enstrümantasyon gerçekten span üretir (bağımlılık denetimi atlanır)."""
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.pool import NullPool

    from tests.conftest import TEST_URL

    disari = InMemorySpanExporter()
    motor = create_async_engine(TEST_URL, poolclass=NullPool)
    try:
        izleme_kur(_uygulama(), motor, Settings(), disaridan=disari)
        async with motor.connect() as baglanti:
            await baglanti.execute(text("SELECT 41 + 1"))
        sql = [
            s
            for s in disari.get_finished_spans()
            if "SELECT 41 + 1" in str((s.attributes or {}).get("db.statement", ""))
        ]
        assert len(sql) == 1
    finally:
        SQLAlchemyInstrumentor().uninstrument()
        await motor.dispose()
