"""S10 migration fan-out testi: kalite/enerji tabloları + CAGG up/down (tenant_alfa)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_TABLOLAR = (
    "kalite_kontrolleri",
    "uygunsuzluklar",
    "capa_aksiyonlari",
    "enerji_tuketim",
    "enerji_tuketim_saatlik",  # continuous aggregate görünümü
)


async def _var_mi(nesne: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        row = await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{nesne}")
        return bool(row)
    finally:
        await conn.close()


async def test_kalite_enerji_up_down(test_db: str) -> None:
    # test_db fixture: head'e migrate edilmiş tenant_alfa şeması.
    for t in _TABLOLAR:
        assert await _var_mi(t), t

    # downgrade bir adım (stok head'ine) → S10 nesneleri gitmeli.
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", "a3d9f1c52e84", db_url=TEST_URL)
    for t in _TABLOLAR:
        assert not await _var_mi(t), t

    # tekrar head'e çık (sonraki testler için durumu geri yükle).
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert await _var_mi("enerji_tuketim_saatlik")
