"""S7 entegrasyon testleri: WebSocket + Redis pub/sub gerçek-zaman akışı.

WebSocket sync ``TestClient`` ile test edilir (httpx WS desteklemez). Yayın, yazma uçlarından
fakeredis üzerinden gelir. Kritik garanti: olay **yalnız** ilgili tenant'ın kanalına düşer
(tenant izolasyonu) ve geçersiz/çapraz-tenant token reddedilir.
"""

from __future__ import annotations

from collections.abc import Iterator

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker
from starlette.websockets import WebSocketDisconnect

from app.core.db.session import get_session
from app.core.security import redis_istemci
from app.main import create_app
from tests.conftest import ALFA, BETA

WS = "/api/v1/ws/olaylar"


@pytest.fixture
def ws_app(test_engine: object) -> Iterator[FastAPI]:
    """Sync TestClient için kurulu app (test DB + fakeredis); kurulu_app'in WS muadili."""
    sm = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)  # type: ignore[arg-type]

    async def _gs() -> object:
        async with sm() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_session] = _gs
    redis_istemci.redis_ayarla(fakeredis.aioredis.FakeRedis(decode_responses=True))
    try:
        yield app
    finally:
        app.dependency_overrides.clear()
        redis_istemci.redis_ayarla(None)


def _giris(client: TestClient, t: dict) -> str:
    r = client.post(
        "/api/v1/kimlik/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


def _h(slug: str, access: str) -> dict[str, str]:
    return {"X-Tenant": slug, "Authorization": f"Bearer {access}"}


def _makine(client: TestClient, h: dict, kod: str) -> int:
    r = client.post("/api/v1/makineler", json={"kod": kod, "ad": kod}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


def test_ws_canli_makine_durum(ws_app: FastAPI) -> None:
    client = TestClient(ws_app)
    access = _giris(client, ALFA)
    h = _h("alfa", access)
    mid = _makine(client, h, "MAK-WS-1")

    with client.websocket_connect(f"{WS}?token={access}&tenant=alfa") as ws:
        client.patch(f"/api/v1/makineler/{mid}/durum", json={"durum": "calisiyor"}, headers=h)
        olay = ws.receive_json()
        assert olay["tur"] == "makine.durum"
        assert olay["makine_id"] == mid
        assert olay["durum"] == "calisiyor"


def test_ws_canli_uretim_eklendi(ws_app: FastAPI) -> None:
    client = TestClient(ws_app)
    access = _giris(client, ALFA)
    h = _h("alfa", access)
    mid = _makine(client, h, "MAK-WS-URETIM")

    with client.websocket_connect(f"{WS}?token={access}&tenant=alfa") as ws:
        client.post(
            "/api/v1/uretim-verileri",
            json={
                "makine_id": mid,
                "planlanan_sure_dk": 480,
                "durus_sure_dk": 30,
                "toplam_adet": 500,
                "saglam_adet": 490,
                "ideal_cevrim_sn": 50,
            },
            headers=h,
        )
        olay = ws.receive_json()
        assert olay["tur"] == "uretim.eklendi"
        assert olay["makine_id"] == mid


def test_ws_tenant_izolasyonu(ws_app: FastAPI) -> None:
    client = TestClient(ws_app)
    a = _giris(client, ALFA)
    b = _giris(client, BETA)
    ha, hb = _h("alfa", a), _h("beta", b)
    amid = _makine(client, ha, "MAK-WS-IZO-A")
    bmid = _makine(client, hb, "MAK-WS-IZO-B")

    with (
        client.websocket_connect(f"{WS}?token={a}&tenant=alfa") as wsa,
        client.websocket_connect(f"{WS}?token={b}&tenant=beta") as wsb,
    ):
        # Alfa'da calisiyor, Beta'da bakimda — durum değeri kanalları ayırt eder.
        client.patch(f"/api/v1/makineler/{amid}/durum", json={"durum": "calisiyor"}, headers=ha)
        client.patch(f"/api/v1/makineler/{bmid}/durum", json={"durum": "bakimda"}, headers=hb)

        oa = wsa.receive_json()
        assert oa["durum"] == "calisiyor" and oa["makine_id"] == amid

        # Beta WS'nin İLK mesajı kendi olayı olmalı — alfa olayını HİÇ almadı (izolasyon).
        ob = wsb.receive_json()
        assert ob["durum"] == "bakimda" and ob["makine_id"] == bmid


def test_ws_gecersiz_token_reddedilir(ws_app: FastAPI) -> None:
    client = TestClient(ws_app)
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"{WS}?token=bozuk-token&tenant=alfa"),
    ):
        pass


def test_ws_capraz_tenant_reddedilir(ws_app: FastAPI) -> None:
    client = TestClient(ws_app)
    access = _giris(client, ALFA)  # alfa token'ı, beta kanalına bağlanmaya çalış
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"{WS}?token={access}&tenant=beta"),
    ):
        pass
