"""S32 (ADR-0051) entegrasyon: bilinen seriyle emisyon toplulaştırma (faktör değişimi, gece yarısı
sınırı İstanbul saatine göre, faktörsüz tüketim), yoğunluk, faktör yönetimi, RBAC, izolasyon, async
ESG raporu (202 → hazır, nesne deposuna yazılır), göç up/down.

Seri 2025 Mart'ındadır: diğer testlerin "şimdi" ölçümlerinden ayrı bir pencere."""

from __future__ import annotations

import asyncio
import io
import uuid
from collections.abc import AsyncIterator
from typing import Any

import asyncpg
import fakeredis
import openpyxl
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.db import fanout
from app.core.security import redis_istemci
from app.modules.dys.depolama import BellekNesneDepo, nesne_depo_ayarla
from app.modules.rapor import service as rapor_service
from tests.conftest import ALFA, BETA, TEST_URL, onayci_basliklari

API = "/api/v1"
_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_S31 = "b2d4f6a8c0e3"
PENCERE = "baslangic=2025-03-10&bitis=2025-03-11"


async def _giris(istemci: AsyncClient, t: dict[str, str]) -> dict[str, str]:
    r = await istemci.post(
        f"{API}/kimlik/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return {"X-Tenant": t["slug"], "Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def _post(istemci: AsyncClient, h: dict[str, str], yol: str, govde: dict[str, Any]) -> Any:
    r = await istemci.post(f"{API}{yol}", json=govde, headers=h)
    assert r.status_code in (200, 201), r.text
    return r.json()["data"]


async def _seri(istemci: AsyncClient, h: dict[str, str]) -> None:
    makine = await _post(
        istemci, h, "/makineler", {"kod": f"S32-{uuid.uuid4().hex[:6]}", "ad": "Pres"}
    )
    olcumler = [
        ("2025-03-10T10:00:00+03:00", "elektrik", 100, "kWh"),
        ("2025-03-10T15:00:00+03:00", "elektrik", 50, "kWh"),
        ("2025-03-10T23:30:00+03:00", "elektrik", 1, "kWh"),
        # 00:30 İstanbul = 10 Mart 21:30 UTC: UTC gününe göre kovalansa 10 Mart'a düşerdi.
        ("2025-03-11T00:30:00+03:00", "elektrik", 200, "kWh"),
        ("2025-03-11T09:00:00+03:00", "dogalgaz", 10, "m3"),
        ("2025-03-11T09:00:00+03:00", "hava", 30, "m3"),
        ("2025-03-12T09:00:00+03:00", "elektrik", 999, "kWh"),  # pencere dışı
    ]
    for zaman, tur, miktar, birim in olcumler:
        await _post(
            istemci,
            h,
            "/enerji-tuketimleri",
            {"zaman": zaman, "enerji_turu": tur, "tuketim": miktar, "birim": birim},
        )
    for zaman, adet in (("2025-03-10T12:00:00+03:00", 70), ("2025-03-11T12:00:00+03:00", 30)):
        await _post(
            istemci,
            h,
            "/uretim-verileri",
            {
                "makine_id": makine["id"],
                "zaman": zaman,
                "planlanan_sure_dk": 60,
                "durus_sure_dk": 0,
                "toplam_adet": adet,
                "saglam_adet": adet,
                "ideal_cevrim_sn": 30,
            },
        )


async def _faktorler(istemci: AsyncClient, h: dict[str, str]) -> None:
    for govde in (
        {"enerji_turu": "elektrik", "birim": "kWh", "deger": "0.5", "kapsam": "kapsam2",
         "gecerlilik": "2020-01-01", "kaynak": "test: eski şebeke"},
        {"enerji_turu": "elektrik", "birim": "kwh", "deger": "0.4", "kapsam": "kapsam2",
         "gecerlilik": "2025-03-11", "kaynak": "test: yeni şebeke"},
        {"enerji_turu": "dogalgaz", "birim": "m³", "deger": "2", "kapsam": "kapsam1",
         "gecerlilik": "2020-01-01", "kaynak": "test: gaz"},
    ):  # fmt: skip
        await _post(istemci, h, "/esg/faktorler", govde)


async def test_bilinen_seri_gunluk_ve_aylik(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    await _seri(kurulu_istemci, h)
    await _faktorler(kurulu_istemci, h)

    r = await kurulu_istemci.get(f"{API}/esg/ozet?{PENCERE}&donem=gun", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    g = {x["donem"]: x for x in d["donemler"]}
    # 10 Mart: 151 kWh × 0,5 = 75,5 kg; 11 Mart: 200 × 0,4 (yeni faktör) = 80, gaz 10 × 2 = 20.
    assert (g["2025-03-10"]["kapsam2_kg"], g["2025-03-10"]["kapsam1_kg"]) == (75.5, 0)
    assert (g["2025-03-11"]["kapsam2_kg"], g["2025-03-11"]["kapsam1_kg"]) == (80, 20)
    assert (g["2025-03-10"]["elektrik_kwh"], g["2025-03-11"]["elektrik_kwh"]) == (151, 200)
    assert (g["2025-03-10"]["saglam_adet"], g["2025-03-10"]["kg_adet"]) == (70, round(75.5 / 70, 4))
    assert d["saglam_adet"] == 100 and d["kg_adet"] == 1.755 and d["kwh_adet"] == 3.51
    assert d["kapsam1_ton"] == 0.02 and abs(d["kapsam2_ton"] - 0.1555) < 0.001
    # Faktörsüz tüketim 0 sayılmaz, ayrıca döner.
    assert [(x["enerji_turu"], x["birim"], x["miktar"]) for x in d["faktorsuz"]] == [
        ("hava", "m3", 30)
    ]
    elk = next(t for t in d["turler"] if t["enerji_turu"] == "elektrik")
    assert (elk["miktar"], elk["emisyon_kg"]) == (351, 155.5)

    # Aylık kırılım: faktör dönem başında (1 Mart) seçilir → bütün Mart 0,5.
    r = await kurulu_istemci.get(
        f"{API}/esg/ozet?baslangic=2025-03-01&bitis=2025-03-31&donem=ay", headers=h
    )
    ay = r.json()["data"]["donemler"]
    assert [(x["donem"], x["kapsam2_kg"], x["kapsam1_kg"]) for x in ay] == [
        ("2025-03-01", (151 + 200 + 999) * 0.5, 20)
    ]

    # Aralık doğrulaması.
    r = await kurulu_istemci.get(f"{API}/esg/ozet?baslangic=2025-03-11&bitis=2025-03-10", headers=h)
    assert r.status_code == 422
    r = await kurulu_istemci.get(
        f"{API}/esg/ozet?baslangic=2025-01-01&bitis=2025-12-31&donem=gun", headers=h
    )
    assert r.status_code == 422


async def test_faktor_yonetimi_rbac_ve_izolasyon(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    govde = {"enerji_turu": "dogalgaz", "birim": "m3", "deger": "1.9", "kapsam": "kapsam1",
             "gecerlilik": "2024-06-01", "kaynak": "test"}  # fmt: skip
    f = await _post(kurulu_istemci, h, "/esg/faktorler", govde)
    assert f["koken"] == "tenant" and f["birim"] == "m3"
    r = await kurulu_istemci.post(f"{API}/esg/faktorler", json=govde, headers=h)
    assert r.status_code == 409
    r = await kurulu_istemci.post(
        f"{API}/esg/faktorler",
        json={**govde, "birim": "MWh", "gecerlilik": "2024-07-01"},
        headers=h,
    )
    assert r.status_code == 422  # faktör temel birim başına
    r = await kurulu_istemci.post(
        f"{API}/esg/faktorler", json={**govde, "enerji_turu": "kömür"}, headers=h
    )
    assert r.status_code == 422
    r = await kurulu_istemci.get(f"{API}/esg/faktorler", headers=h)
    assert any(x["id"] == f["id"] for x in r.json()["data"])

    # RBAC: ESG sorumlusu okur ve yazar; satış temsilcisi okuyamaz.
    esg = await onayci_basliklari(kurulu_istemci, h, roller=("esg",))
    r = await kurulu_istemci.get(f"{API}/esg/ozet?{PENCERE}", headers=esg)
    assert r.status_code == 200
    satis = await onayci_basliklari(kurulu_istemci, h, roller=("satis",))
    r = await kurulu_istemci.get(f"{API}/esg/ozet?{PENCERE}", headers=satis)
    assert r.status_code == 403
    r = await kurulu_istemci.delete(f"{API}/esg/faktorler/{f['id']}", headers=satis)
    assert r.status_code == 403

    # İzolasyon: BETA, ALFA'nın faktörünü silemez, ALFA'nın tüketimini görmez.
    beta = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.delete(f"{API}/esg/faktorler/{f['id']}", headers=beta)
    assert r.status_code == 404
    r = await kurulu_istemci.get(f"{API}/esg/ozet?{PENCERE}", headers=beta)
    assert r.json()["data"]["donemler"] == [] and r.json()["data"]["toplam_ton"] == 0

    r = await kurulu_istemci.delete(f"{API}/esg/faktorler/{f['id']}", headers=esg)
    assert r.status_code == 204


@pytest_asyncio.fixture
async def rapor_ortam(test_engine: AsyncEngine) -> AsyncIterator[BellekNesneDepo]:
    depo = BellekNesneDepo()
    sm = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    rapor_service.oturum_fabrikasi_ayarla(sm)
    rapor_service.es_zamanli_ayarla(True)
    nesne_depo_ayarla(depo)
    redis_istemci.redis_ayarla(fakeredis.aioredis.FakeRedis(decode_responses=True))
    yield depo
    rapor_service.oturum_fabrikasi_ayarla(None)
    rapor_service.es_zamanli_ayarla(False)
    nesne_depo_ayarla(None)
    redis_istemci.redis_ayarla(None)


async def test_esg_raporu_async(kurulu_istemci: AsyncClient, rapor_ortam: BellekNesneDepo) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        f"{API}/raporlar", json={"tur": "esg", "bicim": "xlsx", "gun": 30}, headers=h
    )
    assert r.status_code == 202, r.text
    rid = r.json()["data"]["id"]
    r = await kurulu_istemci.get(f"{API}/raporlar/{rid}", headers=h)
    assert r.json()["data"]["durum"] == "hazir", r.text
    r = await kurulu_istemci.get(f"{API}/raporlar/{rid}/indir", headers=h)
    assert r.status_code == 200
    ws = openpyxl.load_workbook(io.BytesIO(r.content)).active
    assert ws is not None
    hucreler = [str(c.value) for row in ws.iter_rows(max_row=10) for c in row if c.value]
    assert "Kapsam 2 (kg)" in hucreler and any("Sürdürülebilirlik" in x for x in hucreler)

    # esg:oku olmayan (rapor yazabilen) kullanıcı ESG raporu üretemez.
    analist = await onayci_basliklari(kurulu_istemci, h, roller=("analist",))
    r = await kurulu_istemci.post(
        f"{API}/raporlar", json={"tur": "esg", "bicim": "pdf", "gun": 30}, headers=analist
    )
    assert r.status_code == 403, r.text


async def _tablo(t: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{t}"))
    finally:
        await conn.close()


async def test_s32_goc_up_down(test_db: str) -> None:
    assert await _tablo("emisyon_faktorleri")
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _S31, db_url=TEST_URL)
    assert not await _tablo("emisyon_faktorleri")
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert await _tablo("emisyon_faktorleri")
