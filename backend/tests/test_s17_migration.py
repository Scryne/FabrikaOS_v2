"""S17 public migration testi: platform_yonetici/tenant_ihraclari/platform_denetim_izi up/down."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_TABLOLAR = ("platform_yonetici", "tenant_ihraclari", "platform_denetim_izi")


async def _sorgu(sql: str, *args: object) -> object:
    conn = await asyncpg.connect(_DSN)
    try:
        return await conn.fetchval(sql, *args)
    finally:
        await conn.close()


async def _var_mi(tablo: str) -> bool:
    return bool(await _sorgu("SELECT to_regclass($1) IS NOT NULL", f"public.{tablo}"))


async def test_s17_tablolari_head_de_mevcut(test_db: str) -> None:
    for t in _TABLOLAR:
        assert await _var_mi(t), t
    # FK: tenant_ihraclari.tenant_id -> tenant.id (CASCADE — tenant silinince ihraç kaydı da gider).
    assert bool(
        await _sorgu(
            "SELECT 1 FROM pg_constraint WHERE conname = 'fk_tenant_ihraclari_tenant_id_tenant'"
        )
    )


async def test_s17_public_down_up_roundtrip(test_db: str) -> None:
    await asyncio.to_thread(fanout.public_indir, "e7c3a9f1b246", db_url=TEST_URL)
    for t in _TABLOLAR:
        assert not await _var_mi(t), t
    # S16 tabloları down'dan etkilenmez.
    assert await _var_mi("planlar")

    # Tekrar head'e çık (sonraki testler için durumu geri yükle).
    await asyncio.to_thread(fanout.public_yukselt, "head", db_url=TEST_URL)
    for t in _TABLOLAR:
        assert await _var_mi(t), t
