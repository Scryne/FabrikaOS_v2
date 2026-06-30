"""S8 cihaz yönetimi API entegrasyon testleri (RBAC + tenant izolasyonu)."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import ALFA, BETA

pytestmark = pytest.mark.asyncio


async def _giris(c: AsyncClient, t: dict) -> dict[str, str]:
    r = await c.post(
        "/api/v1/kimlik/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return {"X-Tenant": t["slug"], "Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def test_cihaz_olustur_ve_listele(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        "/api/v1/saha/cihazlar", json={"kod": "GW-API", "ad": "API GW"}, headers=h
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["protokol"] == "simulasyon"

    r2 = await kurulu_istemci.get("/api/v1/saha/cihazlar?arama=GW-API", headers=h)
    assert r2.status_code == 200
    assert r2.json()["meta"]["toplam"] >= 1


async def test_cihaz_kimliksiz_401(kurulu_istemci: AsyncClient) -> None:
    # Tenant çözülebilir (X-Tenant var) ama token yok → 401 (tenant'sız olsaydı 404 olurdu).
    r = await kurulu_istemci.get("/api/v1/saha/cihazlar", headers={"X-Tenant": "alfa"})
    assert r.status_code == 401


async def test_cihaz_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = await _giris(kurulu_istemci, ALFA)
    hb = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.post(
        "/api/v1/saha/cihazlar", json={"kod": "GW-IZO", "ad": "İzo GW"}, headers=ha
    )
    cid = r.json()["data"]["id"]
    # beta bu cihazı görememeli
    r2 = await kurulu_istemci.get(f"/api/v1/saha/cihazlar/{cid}", headers=hb)
    assert r2.status_code == 404
