"""Bulut Ingestion Worker — MQTT abonesi (aiomqtt), saha ölçümlerini tenant şemasına yazar.

Çalıştırma: ``python -m app.ingestion.worker``. ``fabrikaos/+/+/olcum`` topic'ine abone olur;
her mesaj için tenant doğrular, ``search_path``'i ayarlar, idempotent yazar, gerçek-zaman
``uretim.eklendi`` olayını yayınlar. Her mesaj log korelasyonu için ``tenant_slug_ctx``/
``request_id_ctx`` set eder. Hata izole edilir — döngü tek bozuk mesajla çökmez.
"""

from __future__ import annotations

import asyncio
import logging
from uuid import uuid4

import aiomqtt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.context import request_id_ctx, tenant_slug_ctx
from app.core.db.tenancy import search_path_ayarla, tenant_bul
from app.core.gercekzaman import yayinla
from app.core.logging import yapilandir_loglama
from app.ingestion.isleyici import MesajGecersiz, mesaj_coz
from app.ingestion.service import olcum_yaz_toplu

logger = logging.getLogger("app.ingestion.worker")

TOPIC = "fabrikaos/+/+/olcum"


async def mesaj_ele(sm: async_sessionmaker[AsyncSession], topic: str, payload: bytes) -> None:
    """Tek MQTT mesajını işler. Bozuk/bilinmeyen → güvenle düşürür (asla yükseltmez)."""
    try:
        slug, cihaz_kod, paket = mesaj_coz(topic, payload)
    except MesajGecersiz:
        logger.warning("geçersiz mesaj düşürüldü: topic=%s", topic)
        return

    t_slug = tenant_slug_ctx.set(slug)
    t_req = request_id_ctx.set(str(uuid4()))
    try:
        etkilenen: tuple[int, ...] = ()
        async with sm() as session, session.begin():
            tenant = await tenant_bul(session, slug)
            if tenant is None or not tenant.aktif:
                logger.warning("bilinmeyen/pasif tenant, düşürüldü: slug=%s", slug)
                return
            await search_path_ayarla(session, slug)
            sonuc = await olcum_yaz_toplu(session, cihaz_kod=cihaz_kod, paketler=[paket])
            etkilenen = sonuc.etkilenen_makineler
        for makine_id in etkilenen:
            await yayinla(slug, {"tur": "uretim.eklendi", "makine_id": makine_id, "kaynak": "saha"})
    except Exception:  # noqa: BLE001 — tek mesaj döngüyü düşürmez
        logger.exception("ingestion mesaj işleme hatası: topic=%s", topic)
    finally:
        tenant_slug_ctx.reset(t_slug)
        request_id_ctx.reset(t_req)


async def calistir(*, broker_host: str, broker_port: int, db_url: str) -> None:
    """MQTT'ye bağlanır ve süresiz dinler."""
    engine = create_async_engine(db_url, poolclass=NullPool)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    logger.info("ingestion worker başlıyor: broker=%s:%s", broker_host, broker_port)
    try:
        async with aiomqtt.Client(broker_host, port=broker_port) as client:
            await client.subscribe(TOPIC)
            async for message in client.messages:
                await mesaj_ele(sm, str(message.topic), message.payload)
    finally:
        await engine.dispose()


def main() -> None:
    s = get_settings()
    yapilandir_loglama(s.log_level)
    asyncio.run(calistir(broker_host=s.mqtt_host, broker_port=s.mqtt_port, db_url=s.database_url))


if __name__ == "__main__":
    main()
