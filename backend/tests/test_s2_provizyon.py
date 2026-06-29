"""S2 provizyonlama testi: idempotentlik.

Aynı tenant'ı iki kez provizyonlamak veriyi bozmaz/çoğaltmaz.
"""

from __future__ import annotations

import asyncio

import asyncpg

from app.control_plane.provizyon import tenant_provizyonla
from app.kimlik.izinler import IZIN_KATALOGU, VARSAYILAN_ROLLER

ASYNCPG_URL = "postgresql://fabrikaos:fabrikaos@localhost:5432/fabrikaos_test"


async def _sayimlar(sema: str) -> dict[str, int]:
    c = await asyncpg.connect(ASYNCPG_URL)
    try:
        await c.execute(f'SET search_path TO "{sema}", public')
        return {
            "kullanici": await c.fetchval("select count(*) from kullanici"),
            "izin": await c.fetchval("select count(*) from izin"),
            "rol": await c.fetchval("select count(*) from rol"),
            "admin": await c.fetchval(
                "select count(*) from kullanici where eposta=$1", "admin@idem.test"
            ),
        }
    finally:
        await c.close()


def test_provizyon_idempotent(test_db: str) -> None:
    ortak = {
        "slug": "idem",
        "ad": "Idempotent Fabrika",
        "admin_eposta": "admin@idem.test",
        "admin_parola": "Idem12345!",
        "db_url": test_db,
    }
    id1 = asyncio.run(tenant_provizyonla(**ortak))
    id2 = asyncio.run(tenant_provizyonla(**ortak))  # ikinci kez: bozmamalı

    assert id1 == id2  # aynı public.tenant kaydı

    s = asyncio.run(_sayimlar("tenant_idem"))
    assert s["admin"] == 1  # admin çoğalmadı
    assert s["kullanici"] == 1
    assert s["izin"] == len(IZIN_KATALOGU)  # izinler çoğalmadı
    assert s["rol"] == len(VARSAYILAN_ROLLER)
