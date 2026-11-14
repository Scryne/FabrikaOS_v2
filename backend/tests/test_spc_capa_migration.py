"""SPC → CAPA köprüsü göçü (e7a9c1d3f5b2): sütun up/down (tenant_alfa)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_ONCEKI = "c3e5a7b9d1f4"  # S32 ESG


async def _sutun_var() -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(
            await conn.fetchval(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = "
                "'tenant_alfa' AND table_name = 'uygunsuzluklar' "
                "AND column_name = 'kaynak_spc_alt_grup_id')"
            )
        )
    finally:
        await conn.close()


async def test_spc_capa_kopru_up_down(test_db: str) -> None:
    assert await _sutun_var()
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _ONCEKI, db_url=TEST_URL)
    assert not await _sutun_var()
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert await _sutun_var()
