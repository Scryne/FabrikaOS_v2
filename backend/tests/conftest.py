"""Test fixture'ları.

İki katman:
- Hafif (DB'siz): ``app`` / ``istemci`` — sağlık ve saf birim testleri için.
- Kurulu (DB'li): ``kurulu_app`` / ``kurulu_istemci`` — ``fabrikaos_test`` veritabanına
  bağlı; public migrate + iki tenant (alfa, beta) provizyonlanmış, ``get_session``
  test motoruna yönlendirilmiş, Redis fakeredis ile değiştirilmiş.

Entegrasyon testleri çalışan bir PostgreSQL gerektirir (``docker compose up db``).
URL ``TEST_DATABASE_URL`` ile override edilebilir (CI için).
"""

from __future__ import annotations

import asyncio
import os
import sys
from collections.abc import AsyncIterator, Iterator

import asyncpg
import fakeredis.aioredis
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.control_plane.provizyon import tenant_provizyonla
from app.core.db import fanout
from app.core.db.session import get_session
from app.core.security import redis_istemci
from app.main import create_app

# aiomqtt/paho, Windows ProactorEventLoop'ta add_reader/add_writer desteklemez (S8 round-trip).
# SelectorEventLoop'a geç → yerel Windows'u Linux CI ile hizalar (Linux varsayılanı zaten Selector).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_SUNUCU = "postgresql://fabrikaos:fabrikaos@localhost:5432"
_TEST_DB = "fabrikaos_test"
TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    f"postgresql+asyncpg://fabrikaos:fabrikaos@localhost:5432/{_TEST_DB}",
)

ALFA = {"slug": "alfa", "ad": "Alfa Fabrika", "eposta": "admin@alfa.test", "parola": "Alfa12345!"}
BETA = {"slug": "beta", "ad": "Beta Fabrika", "eposta": "admin@beta.test", "parola": "Beta12345!"}


# --- Hafif fixture'lar (mevcut, DB'siz) ---
@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest_asyncio.fixture
async def istemci(app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# --- Kurulu (DB'li) fixture'lar ---
async def _db_sifirla() -> None:
    sys = await asyncpg.connect(f"{_SUNUCU}/fabrikaos")
    try:
        await sys.execute(f"DROP DATABASE IF EXISTS {_TEST_DB} WITH (FORCE)")
        await sys.execute(f"CREATE DATABASE {_TEST_DB}")
    finally:
        await sys.close()


async def _tenantlari_provizyonla() -> None:
    for t in (ALFA, BETA):
        await tenant_provizyonla(
            slug=t["slug"],
            ad=t["ad"],
            admin_eposta=t["eposta"],
            admin_parola=t["parola"],
            db_url=TEST_URL,
        )


@pytest.fixture(scope="session")
def test_db() -> str:
    """Test veritabanını sıfırlar, public migrate eder, iki tenant provizyonlar."""
    asyncio.run(_db_sifirla())
    fanout.public_yukselt(db_url=TEST_URL)
    asyncio.run(_tenantlari_provizyonla())
    return TEST_URL


@pytest.fixture(scope="session")
def test_engine(test_db: str) -> Iterator[object]:
    # NullPool: her test kendi event loop'unda; havuzlanmış bağlantı loop'lar arası sızmaz.
    engine = create_async_engine(TEST_URL, poolclass=NullPool)
    yield engine
    asyncio.run(engine.dispose())


@pytest_asyncio.fixture
async def kurulu_app(test_engine: object) -> AsyncIterator[FastAPI]:
    sm = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)  # type: ignore[arg-type]

    async def _test_get_session() -> AsyncIterator[object]:
        async with sm() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_session] = _test_get_session
    redis_istemci.redis_ayarla(fakeredis.aioredis.FakeRedis(decode_responses=True))
    try:
        yield app
    finally:
        app.dependency_overrides.clear()
        redis_istemci.redis_ayarla(None)


@pytest_asyncio.fixture
async def kurulu_istemci(kurulu_app: FastAPI) -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=kurulu_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
