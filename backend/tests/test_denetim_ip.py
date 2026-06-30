"""Denetim izinde istemci IP'sinin (``ip_adresi``) yakalandığını doğrular.

IP, ``RequestContextMiddleware`` tarafından ASGI ``client``'tan istek bağlamına yazılır;
``denetim_yaz`` bunu varsayılan olarak okur. Böylece her yazma ucu ayrıca IP geçirmeden
adli iz tam olur. Tenant şemasına asyncpg ile doğrudan bakılır (test introspection'ı).
"""

from __future__ import annotations

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


async def _denetim_kayitlari(sema: str, eylem: str) -> list[asyncpg.Record]:
    c = await asyncpg.connect(ASYNCPG_URL)
    try:
        return await c.fetch(
            f'SELECT eylem, ip_adresi, request_id FROM "{sema}".denetim_izi '
            "WHERE eylem = $1 ORDER BY id DESC",
            eylem,
        )
    finally:
        await c.close()


async def test_giris_denetiminde_ip_yakalanir(kurulu_istemci: AsyncClient) -> None:
    # Giriş bir "giris" denetim kaydı yazar; IP istek bağlamından gelmeli.
    await _giris(kurulu_istemci, ALFA)
    kayitlar = await _denetim_kayitlari("tenant_alfa", "giris")
    assert kayitlar, "giriş denetim kaydı bulunamadı"
    # httpx ASGITransport varsayılan istemcisi 127.0.0.1; IP NULL olmamalı.
    assert kayitlar[0]["ip_adresi"] == "127.0.0.1", dict(kayitlar[0])


async def test_yazma_denetiminde_ip_yakalanir(kurulu_istemci: AsyncClient) -> None:
    # Makine oluşturma (uretim:yaz) denetim kaydının da IP'si dolu olmalı.
    h = {"X-Tenant": "alfa", "Authorization": f"Bearer {await _giris(kurulu_istemci, ALFA)}"}
    r = await kurulu_istemci.post(
        "/api/v1/makineler", json={"kod": "MAK-IP-1", "ad": "IP testi"}, headers=h
    )
    assert r.status_code == 201, r.text
    kayitlar = await _denetim_kayitlari("tenant_alfa", "olustur")
    makine_kayit = next((k for k in kayitlar if k["ip_adresi"] is not None), None)
    assert makine_kayit is not None, "IP'li 'olustur' denetim kaydı yok"
    assert makine_kayit["ip_adresi"] == "127.0.0.1", dict(makine_kayit)
