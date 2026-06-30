"""S8 REST/CSV ingestion — edge izni, OEE'ye akış, idempotency, CSV."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from tests.conftest import ALFA

pytestmark = pytest.mark.asyncio


async def _giris(c: AsyncClient, t: dict) -> dict[str, str]:
    r = await c.post(
        "/api/v1/kimlik/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    return {"X-Tenant": t["slug"], "Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def _hazirla(c: AsyncClient, h: dict, *, cihaz: str, makine: str) -> None:
    await c.post("/api/v1/saha/cihazlar", json={"kod": cihaz, "ad": cihaz}, headers=h)
    await c.post("/api/v1/makineler", json={"kod": makine, "ad": makine}, headers=h)


def _paket(makine_kod: str) -> dict:
    return {
        "olcum_id": str(uuid.uuid4()),
        "makine_kod": makine_kod,
        "zaman": datetime.now(UTC).isoformat(),
        "vardiya": "A",
        "planlanan_sure_dk": 60,
        "durus_sure_dk": 5,
        "toplam_adet": 100,
        "saglam_adet": 98,
        "ideal_cevrim_sn": 30,
    }


async def test_rest_olcum_oee_panosuna_akar(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    await _hazirla(kurulu_istemci, h, cihaz="GW-O1", makine="MAK-O1")
    r = await kurulu_istemci.post(
        "/api/v1/saha/olcumler",
        json={"cihaz_kod": "GW-O1", "olcumler": [_paket("MAK-O1")]},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["yazilan"] == 1
    # OEE özeti artık bu makineyi yansıtır (elle giriş yok)
    ozet = await kurulu_istemci.get("/api/v1/oee/ozet", headers=h)
    kodlar = [s["makine_kod"] for s in ozet.json()["data"]]
    assert "MAK-O1" in kodlar


async def test_rest_idempotent(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    await _hazirla(kurulu_istemci, h, cihaz="GW-O2", makine="MAK-O2")
    p = _paket("MAK-O2")
    govde = {"cihaz_kod": "GW-O2", "olcumler": [p]}
    await kurulu_istemci.post("/api/v1/saha/olcumler", json=govde, headers=h)
    r2 = await kurulu_istemci.post("/api/v1/saha/olcumler", json=govde, headers=h)
    assert r2.status_code == 201
    assert r2.json()["data"]["atlanan"] == 1 and r2.json()["data"]["yazilan"] == 0


async def test_olcum_kimliksiz_401(kurulu_istemci: AsyncClient) -> None:
    # Tenant çözülebilir (X-Tenant var) ama token yok → 401.
    r = await kurulu_istemci.post(
        "/api/v1/saha/olcumler",
        json={"cihaz_kod": "X", "olcumler": [_paket("Y")]},
        headers={"X-Tenant": "alfa"},
    )
    assert r.status_code == 401


async def test_csv_ice_aktar(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    await _hazirla(kurulu_istemci, h, cihaz="GW-CSV", makine="MAK-CSV")
    csv_metin = (
        "makine_kod,zaman,vardiya,planlanan_sure_dk,durus_sure_dk,"
        "toplam_adet,saglam_adet,ideal_cevrim_sn\n"
        f"MAK-CSV,{datetime.now(UTC).isoformat()},A,60,5,100,98,30\n"
    )
    r = await kurulu_istemci.post(
        "/api/v1/saha/olcumler/csv",
        params={"cihaz_kod": "GW-CSV"},
        files={"dosya": ("olcum.csv", csv_metin, "text/csv")},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["yazilan"] == 1
