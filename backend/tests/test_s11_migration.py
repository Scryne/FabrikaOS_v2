"""S11 migration fan-out testi: İSG/İK tabloları up/down (tenant_alfa)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_ONCEKI = "b7e4c2f9a016"  # S10 (kalite/enerji) head — S11 nesneleri bunun üstünde
_TABLOLAR = (
    "personel",
    "is_kazalari",
    "risk_degerlendirmeleri",
    "izin_talepleri",
    "fazla_mesailer",
    "zimmetler",
    "sertifikalar",
)


async def _var_mi(nesne: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(
            await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{nesne}")
        )
    finally:
        await conn.close()


async def test_isg_ik_up_down(test_db: str) -> None:
    # test_db fixture: head'e migrate edilmiş tenant_alfa şeması.
    for t in _TABLOLAR:
        assert await _var_mi(t), t

    # downgrade bir adım (S10 head'ine) → S11 tabloları gitmeli.
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _ONCEKI, db_url=TEST_URL)
    for t in _TABLOLAR:
        assert not await _var_mi(t), t

    # tekrar head'e çık (sonraki testler için durumu geri yükle).
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert await _var_mi("personel")
