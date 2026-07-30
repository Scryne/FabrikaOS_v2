"""S23 migration fan-out testi: güvenlik & uyum nesneleri up/down (tenant_alfa + public)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_ONCEKI = "c4a7f3e9b528"  # S24 head — S23 nesneleri bunun üstünde
_TABLOLAR = ("kurtarma_kodlari", "oturumlar", "kvkk_ihraclari", "consent_kayitlari")
_KOLONLAR = (
    ("kullanici", "totp_sirri"),
    ("kullanici", "iki_asama_aktif"),
    # e5b1c7d4a238 — KVKK artefakt saklama süresi (sertleştirme turu).
    ("kvkk_ihraclari", "gecerlilik_bitisi"),
    ("kvkk_ihraclari", "indirme_sayisi"),
)


async def _sorgu(sql: str, *args: object) -> object:
    conn = await asyncpg.connect(_DSN)
    try:
        return await conn.fetchval(sql, *args)
    finally:
        await conn.close()


async def _tablo_var_mi(nesne: str) -> bool:
    return bool(await _sorgu("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{nesne}"))


async def _kolon_var_mi(sema: str, tablo: str, kolon: str) -> bool:
    return bool(
        await _sorgu(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_schema = $1 AND table_name = $2 AND column_name = $3
            )
            """,
            sema,
            tablo,
            kolon,
        )
    )


async def _trigger_var_mi() -> bool:
    return bool(
        await _sorgu(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.triggers
                WHERE trigger_schema = 'tenant_alfa' AND trigger_name = 'denetim_izi_koru_tg'
            )
            """
        )
    )


async def test_s23_up_down(test_db: str) -> None:
    for t in _TABLOLAR:
        assert await _tablo_var_mi(t), t
    for tablo, kolon in _KOLONLAR:
        assert await _kolon_var_mi("tenant_alfa", tablo, kolon), f"{tablo}.{kolon}"
    assert await _kolon_var_mi("public", "tenant", "guvenlik_ayarlari")
    assert await _trigger_var_mi()

    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _ONCEKI, db_url=TEST_URL)
    for t in _TABLOLAR:
        assert not await _tablo_var_mi(t), t
    for tablo, kolon in _KOLONLAR:
        assert not await _kolon_var_mi("tenant_alfa", tablo, kolon), f"{tablo}.{kolon}"
    assert not await _trigger_var_mi()

    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    for t in _TABLOLAR:
        assert await _tablo_var_mi(t), t
    for tablo, kolon in _KOLONLAR:
        assert await _kolon_var_mi("tenant_alfa", tablo, kolon), f"{tablo}.{kolon}"
    assert await _trigger_var_mi()
