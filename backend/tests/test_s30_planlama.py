"""S30 (ADR-0049) entegrasyon: çizelge ucu, plan girdisi, EDD/elle sıra, kapasite aşımı, RBAC,
izolasyon, göç up/down. Ufuk ileri bir tarihtir (2030): "şimdi"den ve diğer testlerin vardiya
tanımlarından bağımsız göreli özellikler sınanır."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import asyncpg
from httpx import AsyncClient

from app.core.db import fanout
from tests.conftest import ALFA, BETA, TEST_URL, onayci_basliklari

API = "/api/v1"
_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_S29 = "f8a0c2e4b6d8"
UFUK = "baslangic=2030-01-07&gun=5"


async def _giris(istemci: AsyncClient, t: dict[str, str]) -> dict[str, str]:
    r = await istemci.post(
        f"{API}/kimlik/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return {"X-Tenant": t["slug"], "Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def _makine(istemci: AsyncClient, h: dict[str, str]) -> int:
    r = await istemci.post(
        f"{API}/makineler", json={"kod": f"S30-{uuid.uuid4().hex[:6]}", "ad": "Pres"}, headers=h
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _is_emri(
    istemci: AsyncClient, h: dict[str, str], makine: int, hedef: str, oncelik: str = "orta"
) -> int:
    r = await istemci.post(
        f"{API}/is-emirleri",
        json={"baslik": "Plan işi", "makine_id": makine, "hedef_tarih": hedef, "oncelik": oncelik},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _cizelge(istemci: AsyncClient, h: dict[str, str], makine: int) -> dict[Any, Any]:
    r = await istemci.get(f"{API}/planlama/cizelge?{UFUK}&makine_id={makine}", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert len(veri["makineler"]) == 1
    return {i["is_emri_id"]: i for i in veri["makineler"][0]["isler"]} | {"_m": veri}


async def test_edd_elle_sira_sure_ve_kapasite_asimi(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    m = await _makine(kurulu_istemci, h)
    gec = await _is_emri(kurulu_istemci, h, m, "2030-01-09T12:00:00+03:00")
    erken = await _is_emri(kurulu_istemci, h, m, "2030-01-08T12:00:00+03:00")
    imkansiz = await _is_emri(kurulu_istemci, h, m, "2030-01-06T12:00:00+03:00")  # ufuk öncesi

    c = await _cizelge(kurulu_istemci, h, m)
    # EDD: imkansız (en erken hedef) → erken → geç; süre tahmini yok → varsayılan 60 dk.
    assert c[imkansiz]["baslangic"] < c[erken]["baslangic"] < c[gec]["baslangic"]
    assert {c[x]["sure_kaynagi"] for x in (gec, erken, imkansiz)} == {"varsayilan"}
    assert c[imkansiz]["kapasite_asimi"] and c[imkansiz]["gecikme_dk"] > 0
    assert not c[erken]["kapasite_asimi"] and c[erken]["gecikme_dk"] == 0
    assert c["_m"]["ozet"]["kapasite_asimi"] >= 1
    yuk = c["_m"]["makineler"][0]["gunluk_yuk"]
    assert sum(g["plan_dk"] for g in yuk) == 180.0  # 3 × 60 dk

    # Elle sıra + elle süre: "geç" öne alınır, süresi 90 dk.
    r = await kurulu_istemci.put(
        f"{API}/is-emirleri/{gec}/plan", json={"elle_sira": 1, "sure_dk": 90}, headers=h
    )
    assert r.status_code == 200, r.text
    c = await _cizelge(kurulu_istemci, h, m)
    assert c[gec]["baslangic"] < c[imkansiz]["baslangic"]
    assert c[gec]["sure_kaynagi"] == "elle" and c[gec]["sure_dk"] == 90
    # Tekrarlanabilir: aynı girdi aynı çizelge.
    assert await _cizelge(kurulu_istemci, h, m) == c

    # Girdi silinince EDD'ye döner.
    r = await kurulu_istemci.put(f"{API}/is-emirleri/{gec}/plan", json={}, headers=h)
    assert r.status_code == 200
    c = await _cizelge(kurulu_istemci, h, m)
    assert c[erken]["baslangic"] < c[gec]["baslangic"]


async def test_plan_girdisi_rbac_izolasyon_ve_kapali_is(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    m = await _makine(kurulu_istemci, h)
    ie = await _is_emri(kurulu_istemci, h, m, "2030-01-08T12:00:00+03:00")

    izleyici = await onayci_basliklari(kurulu_istemci, h, roller=("izleyici",))
    r = await kurulu_istemci.get(f"{API}/planlama/cizelge?{UFUK}", headers=izleyici)
    assert r.status_code == 200
    r = await kurulu_istemci.put(
        f"{API}/is-emirleri/{ie}/plan", json={"sure_dk": 30}, headers=izleyici
    )
    assert r.status_code == 403
    planlamaci = await onayci_basliklari(kurulu_istemci, h, roller=("planlamaci",))
    r = await kurulu_istemci.put(
        f"{API}/is-emirleri/{ie}/plan", json={"sure_dk": 30}, headers=planlamaci
    )
    assert r.status_code == 200, r.text

    beta = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.put(f"{API}/is-emirleri/{ie}/plan", json={"sure_dk": 5}, headers=beta)
    assert r.status_code == 404
    r = await kurulu_istemci.get(f"{API}/planlama/cizelge?{UFUK}&makine_id={m}", headers=beta)
    assert r.json()["data"]["makineler"] == []

    r = await kurulu_istemci.put(f"{API}/is-emirleri/{ie}/plan", json={"sure_dk": 0}, headers=h)
    assert r.status_code == 422
    r = await kurulu_istemci.patch(
        f"{API}/is-emirleri/{ie}/durum", json={"durum": "iptal"}, headers=h
    )
    assert r.status_code == 200, r.text
    r = await kurulu_istemci.put(f"{API}/is-emirleri/{ie}/plan", json={"sure_dk": 30}, headers=h)
    assert r.status_code == 409
    c = await kurulu_istemci.get(f"{API}/planlama/cizelge?{UFUK}&makine_id={m}", headers=h)
    assert c.json()["data"]["makineler"] == []  # iptal edilen iş çizelgeye girmez


async def _tablo(t: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{t}"))
    finally:
        await conn.close()


async def test_s30_goc_up_down(test_db: str) -> None:
    assert await _tablo("is_emri_planlari")
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _S29, db_url=TEST_URL)
    assert not await _tablo("is_emri_planlari")
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert await _tablo("is_emri_planlari")
