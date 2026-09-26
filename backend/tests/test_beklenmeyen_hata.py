"""Yakalanmamış istisna: standart 500 zarfı, CORS başlığı ve x-request-id ile döner.

Eskiden Starlette'in dış ``ServerErrorMiddleware``'i yanıtı CORS katmanının dışında
üretiyordu; tarayıcı gerçek hatayı değil "CORS engelledi"yi görüyordu (2026-09-26,
MinIO kapalıyken /tahmin/kestirimci-bakim).
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app

KOKEN = "http://localhost:5173"


def _uygulama(monkeypatch) -> TestClient:  # type: ignore[no-untyped-def]
    get_settings.cache_clear()
    monkeypatch.setenv("CORS_ORIGINS", f'["{KOKEN}"]')
    app = create_app()

    @app.get("/_patla")
    async def _patla() -> None:
        raise RuntimeError("altyapi yok")

    get_settings.cache_clear()
    return TestClient(app, raise_server_exceptions=False)


def test_beklenmeyen_hata_cors_ve_zarfla_doner(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    istemci = _uygulama(monkeypatch)
    r = istemci.get("/_patla", headers={"Origin": KOKEN, "X-Request-Id": "istek-42"})
    assert r.status_code == 500
    assert r.headers["access-control-allow-origin"] == KOKEN
    assert r.headers["x-request-id"] == "istek-42"
    assert r.json() == {
        "success": False,
        "message": "Sunucu hatası",
        "hata_kodu": "SUNUCU",
        "detaylar": [],
    }


def test_beklenmeyen_hata_ic_ayrintiyi_sizdirmaz(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    istemci = _uygulama(monkeypatch)
    r = istemci.get("/_patla", headers={"Origin": KOKEN})
    assert "altyapi yok" not in r.text
