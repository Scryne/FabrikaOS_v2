"""S18 migration fan-out testi: entegrasyon nesneleri up/down (tenant_alfa)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_ONCEKI = "c9e6f2a8d135"  # S15 (ikiz) head — S18 nesneleri bunun üstünde
_TABLOLAR = ("webhook_abonelikleri", "webhook_teslimatlari", "api_anahtarlari")


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


async def test_s18_up_down(test_db: str) -> None:
    # test_db fixture: head'e migrate edilmiş tenant_alfa şeması.
    for t in _TABLOLAR:
        assert await _tablo_var_mi(t), t
    assert await _kolon_var_mi("kullanici", "firma_id")

    # downgrade bir adım (S15 head'ine) → S18 nesneleri gitmeli.
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _ONCEKI, db_url=TEST_URL)
    for t in _TABLOLAR:
        assert not await _tablo_var_mi(t), t
    assert not await _kolon_var_mi("kullanici", "firma_id")

    # tekrar head'e çık (sonraki testler için durumu geri yükle).
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    for t in _TABLOLAR:
        assert await _tablo_var_mi(t), t
    assert await _kolon_var_mi("kullanici", "firma_id")
