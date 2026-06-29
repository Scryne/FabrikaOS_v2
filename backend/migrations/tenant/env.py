"""Alembic env — TENANT ağacı (FAN-OUT). Hedef: bir veya çok ``tenant_<slug>`` şeması.

Hedef şemalar şu sırayla belirlenir:
1. ``config.attributes['schemas']`` (provizyonlama tek şema verir, ör. ``["tenant_a"]``).
2. ``-x schema=...`` (CLI autogenerate için tek şema, ör. ``tenant_sablon``).
3. Yoksa ``public.tenant`` içindeki tüm aktif tenant'lar → ``tenant_<slug>`` (tam fan-out).

Her şema kendi ``alembic_version`` tablosunu tutar (``version_table_schema``).
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.db.registry import tenant_metadata

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = tenant_metadata


def _db_url() -> str:
    url = config.attributes.get("db_url")
    return str(url) if url else get_settings().database_url


def _hedef_semalar(connection: Connection) -> list[str]:
    attr = config.attributes.get("schemas")
    if attr:
        return list(attr)
    x = context.get_x_argument(as_dictionary=True)
    if "schema" in x:
        return [x["schema"]]
    rows = connection.execute(
        text("SELECT 'tenant_' || slug FROM public.tenant WHERE aktif = true ORDER BY slug")
    )
    return [r[0] for r in rows]


def _dahil_et(obj: object, ad: str | None, tur: str, *_: object) -> bool:
    # Alembic'in kendi sürüm tablosunu autogenerate karşılaştırmasından dışla.
    return not (tur == "table" and ad == "alembic_version")


def _do_run_migrations(connection: Connection) -> None:
    semalar = _hedef_semalar(connection)
    for sema in semalar:
        connection.exec_driver_sql(f'SET search_path TO "{sema}", public')
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=sema,
            include_schemas=False,
            compare_type=True,
            include_object=_dahil_et,
        )
        with context.begin_transaction():
            context.run_migrations()


async def _run_online() -> None:
    engine = create_async_engine(_db_url(), poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(_do_run_migrations)
        await connection.commit()
    await engine.dispose()


def run() -> None:
    if context.is_offline_mode():
        raise RuntimeError("Offline mod desteklenmiyor; canlı bağlantı gerekli.")
    asyncio.run(_run_online())


run()
