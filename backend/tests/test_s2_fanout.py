"""S2 migration fan-out testleri (senkron).

DoD: migrasyon ``public`` + en az iki tenant şemasında çalışır ve geri alınabilir (downgrade).
"""

from __future__ import annotations

import asyncio

import asyncpg

from app.core.db import fanout

ASYNCPG_URL = "postgresql://fabrikaos:fabrikaos@localhost:5432/fabrikaos_test"


async def _tablolar(sema: str) -> set[str]:
    c = await asyncpg.connect(ASYNCPG_URL)
    try:
        rows = await c.fetch("select tablename from pg_tables where schemaname = $1", sema)
        return {r["tablename"] for r in rows}
    finally:
        await c.close()


async def _sema_olustur(sema: str) -> None:
    c = await asyncpg.connect(ASYNCPG_URL)
    try:
        await c.execute(f'CREATE SCHEMA IF NOT EXISTS "{sema}"')
    finally:
        await c.close()


async def _sema_sil(sema: str) -> None:
    c = await asyncpg.connect(ASYNCPG_URL)
    try:
        await c.execute(f'DROP SCHEMA IF EXISTS "{sema}" CASCADE')
    finally:
        await c.close()


def test_fanout_public_ve_iki_tenant_uygulandi(test_db: str) -> None:
    # public + alfa + beta: hepsi migrate edilmiş olmalı (fan-out kanıtı).
    public = asyncio.run(_tablolar("public"))
    assert {"tenant", "abonelik", "alembic_version"} <= public

    for sema in ("tenant_alfa", "tenant_beta"):
        t = asyncio.run(_tablolar(sema))
        assert {"kullanici", "rol", "izin", "denetim_izi", "alembic_version"} <= t


def test_fanout_upgrade_downgrade_roundtrip(test_db: str) -> None:
    slug = "gecici"
    sema = f"tenant_{slug}"
    asyncio.run(_sema_sil(slug and sema))
    asyncio.run(_sema_olustur(sema))
    try:
        # upgrade
        fanout.tenant_yukselt_tek(slug, db_url=test_db)
        t = asyncio.run(_tablolar(sema))
        assert "kullanici" in t and "rol_izin" in t

        # downgrade -> base: iş tabloları gider, yalnızca alembic_version kalır
        fanout.tenant_indir_tek(slug, db_url=test_db)
        t = asyncio.run(_tablolar(sema))
        assert "kullanici" not in t
        assert t <= {"alembic_version"}

        # tekrar upgrade -> geri gelir (geri alınabilirlik kanıtı)
        fanout.tenant_yukselt_tek(slug, db_url=test_db)
        t = asyncio.run(_tablolar(sema))
        assert "kullanici" in t
    finally:
        asyncio.run(_sema_sil(sema))
