"""S24 migration fan-out testi: MES derinleşme nesneleri up/down (tenant_alfa)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_ONCEKI = "b3e7c5f9a284"  # S-VB head — S24 nesneleri bunun üstünde
_TABLOLAR = (
    "vardiyalar",
    "durus_nedenleri",
    "durus_kayitlari",
    "urunler",
    "receteler",
    "recete_kalemleri",
)
_KOLONLAR = (
    ("is_emirleri", "urun_id"),
    ("is_emirleri", "miktar"),
    ("is_emirleri", "lot_no"),
    ("is_emirleri", "bakim_plani_id"),
    ("is_emirleri", "ariza_kaydi_id"),
    ("uretim_verileri", "lot_no"),
    ("bakim_planlari", "yedek_parca_malzeme_id"),
)


async def _tablo_var_mi(nesne: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(
            await conn.fetchval("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{nesne}")
        )
    finally:
        await conn.close()


async def _kolon_var_mi(tablo: str, kolon: str) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(
            await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = 'tenant_alfa' AND table_name = $1 AND column_name = $2
                )
                """,
                tablo,
                kolon,
            )
        )
    finally:
        await conn.close()


async def test_s24_up_down(test_db: str) -> None:
    for t in _TABLOLAR:
        assert await _tablo_var_mi(t), t
    for tablo, kolon in _KOLONLAR:
        assert await _kolon_var_mi(tablo, kolon), f"{tablo}.{kolon}"

    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _ONCEKI, db_url=TEST_URL)
    for t in _TABLOLAR:
        assert not await _tablo_var_mi(t), t
    for tablo, kolon in _KOLONLAR:
        assert not await _kolon_var_mi(tablo, kolon), f"{tablo}.{kolon}"

    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    for t in _TABLOLAR:
        assert await _tablo_var_mi(t), t
    for tablo, kolon in _KOLONLAR:
        assert await _kolon_var_mi(tablo, kolon), f"{tablo}.{kolon}"
