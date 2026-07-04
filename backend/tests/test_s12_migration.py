"""S12 migration fan-out testi: CRM/sözleşme/talep/DYS/duyuru tabloları up/down (tenant_alfa)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_ONCEKI = "d5c8e1f0a927"  # S11 (isg/ik) head — S12 nesneleri bunun üstünde
_TABLOLAR = (
    "firmalar",
    "ortaklar",
    "sozlesmeler",
    "talepler",
    "belgeler",
    "belge_surumleri",
    "duyurular",
)


async def _var_mi(nesne: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(
            await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{nesne}")
        )
    finally:
        await conn.close()


async def test_s12_up_down(test_db: str) -> None:
    # test_db fixture: head'e migrate edilmiş tenant_alfa şeması.
    for t in _TABLOLAR:
        assert await _var_mi(t), t

    # downgrade bir adım (S11 head'ine) → S12 tabloları gitmeli.
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _ONCEKI, db_url=TEST_URL)
    for t in _TABLOLAR:
        assert not await _var_mi(t), t

    # tekrar head'e çık (sonraki testler için durumu geri yükle).
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert await _var_mi("firmalar")
