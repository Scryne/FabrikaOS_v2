"""S9 entegrasyon: stok hareketi bakiye + negatif + idempotency + kenar-tetikli stok.kritik."""

from __future__ import annotations

import json

import asyncpg
from httpx import AsyncClient

from tests.conftest import ALFA

KIMLIK = "/api/v1/kimlik"
ASYNCPG_URL = "postgresql://fabrikaos:fabrikaos@localhost:5432/fabrikaos_test"


async def _giris(istemci: AsyncClient, t: dict) -> str:
    r = await istemci.post(
        f"{KIMLIK}/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


def _h(slug: str, access: str) -> dict[str, str]:
    return {"X-Tenant": slug, "Authorization": f"Bearer {access}"}


async def _malzeme_id(istemci: AsyncClient, h: dict[str, str], kod: str, kritik: float = 0) -> int:
    r = await istemci.post(
        "/api/v1/malzemeler",
        json={"kod": kod, "ad": kod, "birim": "adet", "kritik_stok": kritik},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _hareket(
    istemci: AsyncClient,
    h: dict[str, str],
    mid: int,
    tur: str,
    miktar: float,
    anahtar: str | None = None,
) -> tuple[int, dict]:
    bh = dict(h)
    if anahtar is not None:
        bh["Idempotency-Key"] = anahtar
    r = await istemci.post(
        "/api/v1/stok-hareketleri",
        json={"malzeme_id": mid, "tur": tur, "miktar": miktar},
        headers=bh,
    )
    return r.status_code, r.json()


async def _outbox(sema: str, olay_turu: str) -> list[dict]:
    c = await asyncpg.connect(ASYNCPG_URL)
    try:
        rows = await c.fetch(
            f'SELECT govde FROM "{sema}".giden_olaylar WHERE olay_turu = $1 ORDER BY id', olay_turu
        )
        return [json.loads(r["govde"]) if isinstance(r["govde"], str) else r["govde"] for r in rows]
    finally:
        await c.close()


async def test_giris_cikis_bakiye(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-BAK")
    sk, d = await _hareket(kurulu_istemci, h, mid, "giris", 10)
    assert sk == 201, d
    assert d["data"]["bakiye_sonrasi"] == 10
    sk, d = await _hareket(kurulu_istemci, h, mid, "cikis", 4)
    assert d["data"]["bakiye_sonrasi"] == 6
    # malzeme bakiyesi de güncel
    r = await kurulu_istemci.get(f"/api/v1/malzemeler/{mid}", headers=h)
    assert r.json()["data"]["mevcut_miktar"] == 6


async def test_negatif_cikis_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-NEG")
    sk, d = await _hareket(kurulu_istemci, h, mid, "cikis", 1)
    assert sk == 422, d


async def test_duzeltme_mutlak(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-DUZ")
    await _hareket(kurulu_istemci, h, mid, "giris", 10)
    sk, d = await _hareket(kurulu_istemci, h, mid, "duzeltme", 7)
    assert sk == 201, d
    assert d["data"]["bakiye_sonrasi"] == 7


async def test_idempotency_tek_hareket(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-IDEM")
    await _hareket(kurulu_istemci, h, mid, "giris", 5, anahtar="ANAH-1")
    # aynı anahtar → bakiye 1 kez değişti (10 değil 5)
    await _hareket(kurulu_istemci, h, mid, "giris", 5, anahtar="ANAH-1")
    r = await kurulu_istemci.get(f"/api/v1/malzemeler/{mid}", headers=h)
    assert r.json()["data"]["mevcut_miktar"] == 5


async def test_kritik_kenar_tetik_bir_kez(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-KENAR", kritik=5)
    await _hareket(kurulu_istemci, h, mid, "giris", 10)  # 10, eşik üstü
    await _hareket(kurulu_istemci, h, mid, "cikis", 6)  # 4, eşik altına ilk geçiş → olay
    await _hareket(kurulu_istemci, h, mid, "cikis", 1)  # 3, hâlâ altında → YENİ olay yok

    govdeler = [
        g for g in await _outbox("tenant_alfa", "stok.kritik") if g.get("malzeme_id") == mid
    ]
    assert len(govdeler) == 1, govdeler
    assert govdeler[0]["kod"] == "MLZ-KENAR"
    assert govdeler[0]["mevcut_miktar"] == 4


async def test_hareket_listele_filtre(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-LIST")
    await _hareket(kurulu_istemci, h, mid, "giris", 3)
    r = await kurulu_istemci.get(f"/api/v1/stok-hareketleri?malzeme_id={mid}&tur=giris", headers=h)
    assert r.status_code == 200, r.text
    assert all(x["tur"] == "giris" and x["malzeme_id"] == mid for x in r.json()["data"])
    assert "meta" in r.json()
