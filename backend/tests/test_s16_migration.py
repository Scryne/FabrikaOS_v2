"""S16 public migration testi: planlar/modul_haklari/ozellik_bayraklari up/down + seed."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_TABLOLAR = ("planlar", "modul_haklari", "ozellik_bayraklari")


async def _sorgu(sql: str, *args: object) -> object:
    conn = await asyncpg.connect(_DSN)
    try:
        return await conn.fetchval(sql, *args)
    finally:
        await conn.close()


async def _var_mi(tablo: str) -> bool:
    return bool(await _sorgu("SELECT to_regclass($1) IS NOT NULL", f"public.{tablo}"))


async def test_planlar_seed_ve_fk_head_de_mevcut(test_db: str) -> None:
    for t in _TABLOLAR:
        assert await _var_mi(t), t
    # Plan kataloğu seed'lenmiş olmalı (4 plan).
    assert await _sorgu("SELECT count(*) FROM public.planlar") == 4
    assert await _sorgu("SELECT koltuk_limiti FROM public.planlar WHERE kod='deneme'") == 5
    assert await _sorgu("SELECT koltuk_limiti FROM public.planlar WHERE kod='kurumsal'") is None
    # FK: abonelik.plan_kodu -> planlar.kod (geçersiz plan yazılamaz).
    assert bool(
        await _sorgu("SELECT 1 FROM pg_constraint WHERE conname = 'fk_abonelik_plan_kodu_planlar'")
    )


async def test_public_down_up_roundtrip(test_db: str) -> None:
    await asyncio.to_thread(fanout.public_indir, "d6dbf05143e2", db_url=TEST_URL)
    for t in _TABLOLAR:
        assert not await _var_mi(t), t

    # Tekrar head'e çık (sonraki testler için durumu geri yükle) — seed yeniden yazılır.
    await asyncio.to_thread(fanout.public_yukselt, "head", db_url=TEST_URL)
    for t in _TABLOLAR:
        assert await _var_mi(t), t
    assert await _sorgu("SELECT count(*) FROM public.planlar") == 4

    # Migration seed'i STATİKTİR (S16 anındaki katalog); katalog kod tarafında evrildi
    # (S18: +entegrasyon +dis-portal). Operasyondaki prosedürün aynısı: idempotent plan
    # senkronu koş — sonraki testler güncel katalogla çalışsın (S16 operasyon dersi).
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from app.control_plane.provizyon import _plan_tohumla

    engine = create_async_engine(TEST_URL, poolclass=NullPool)
    try:
        await _plan_tohumla(async_sessionmaker(engine, expire_on_commit=False))
    finally:
        await engine.dispose()
    assert await _sorgu("SELECT moduller ? 'dis-portal' FROM public.planlar WHERE kod='kurumsal'")
