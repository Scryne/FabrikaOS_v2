"""Alembic env — PUBLIC (control-plane) ağacı. Tek şema: ``public``.

DB URL ``config.attributes['db_url']`` ile programatik olarak verilebilir; yoksa
ayarlardan (``DATABASE_URL`` / ``.env``) çözülür. Async motor + ``run_sync`` kullanılır.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.core.db.registry import public_metadata

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = public_metadata


def _db_url() -> str:
    url = config.attributes.get("db_url")
    return str(url) if url else get_settings().database_url


def _dahil_et(obj: object, ad: str | None, tur: str, *_: object) -> bool:
    # Alembic'in kendi sürüm tablosunu autogenerate karşılaştırmasından dışla.
    return not (tur == "table" and ad == "alembic_version")


def _do_run_migrations(connection: Connection) -> None:
    connection.exec_driver_sql("SET search_path TO public")
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table_schema="public",
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
