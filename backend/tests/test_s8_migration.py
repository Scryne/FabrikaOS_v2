"""S8 migration fan-out testi: saha tabloları up/down (tenant_alfa şeması)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")


async def _tablo_var_mi(tablo: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(
            await conn.fetchval(
                "SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{tablo}"
            )
        )
    finally:
        await conn.close()


async def test_saha_tablolari_up_down(test_db: str) -> None:
    # test_db fixture: head'e migrate edilmiş tenant_alfa şeması.
    assert await _tablo_var_mi("saha_cihazlar")
    assert await _tablo_var_mi("saha_alinan_olcum")

    # downgrade bir adım → saha tabloları gitmeli (fanout senkron → ayrı thread'de çalıştır).
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", "c5a2f1b8e34d", db_url=TEST_URL)
    assert not await _tablo_var_mi("saha_cihazlar")
    assert not await _tablo_var_mi("saha_alinan_olcum")

    # tekrar head'e çık (sonraki testler için durumu geri yükle)
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert await _tablo_var_mi("saha_cihazlar")
