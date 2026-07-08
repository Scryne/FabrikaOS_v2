"""S15 migration fan-out testi: ikiz_dugumleri tablosu up/down (tenant_alfa)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_ONCEKI = "b4e8f2a6c159"  # S14 (rapor) head — S15 nesneleri bunun üstünde


async def _var_mi(nesne: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(
            await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{nesne}")
        )
    finally:
        await conn.close()


async def test_s15_up_down(test_db: str) -> None:
    # test_db fixture: head'e migrate edilmiş tenant_alfa şeması.
    assert await _var_mi("ikiz_dugumleri")

    # downgrade bir adım (S14 head'ine) → ikiz_dugumleri gitmeli.
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _ONCEKI, db_url=TEST_URL)
    assert not await _var_mi("ikiz_dugumleri")

    # tekrar head'e çık (sonraki testler için durumu geri yükle).
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert await _var_mi("ikiz_dugumleri")
