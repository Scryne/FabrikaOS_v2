"""S9 migration fan-out testi: stok tabloları up/down (tenant_alfa şeması)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_TABLOLAR = (
    "malzemeler",
    "stok_hareketleri",
    "satinalma_talepleri",
    "satinalma_talebi_kalemleri",
)


async def _tablo_var_mi(tablo: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(
            await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{tablo}")
        )
    finally:
        await conn.close()


async def test_stok_tablolari_up_down(test_db: str) -> None:
    # test_db fixture: head'e migrate edilmiş tenant_alfa şeması.
    for t in _TABLOLAR:
        assert await _tablo_var_mi(t), t

    # downgrade bir adım (saha head'ine) → stok tabloları gitmeli.
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", "f3a9c1d72b84", db_url=TEST_URL)
    for t in _TABLOLAR:
        assert not await _tablo_var_mi(t), t

    # tekrar head'e çık (sonraki testler için durumu geri yükle).
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert await _tablo_var_mi("malzemeler")
