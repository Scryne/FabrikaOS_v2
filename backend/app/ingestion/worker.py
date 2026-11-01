"""Bulut Ingestion Worker — MQTT abonesi (aiomqtt), saha ölçümlerini tenant şemasına yazar.

Çalıştırma: ``python -m app.ingestion.worker``. ``fabrikaos/+/+/olcum`` topic'ine abone olur;
her mesaj için tenant doğrular, ``search_path``'i ayarlar, idempotent yazar, gerçek-zaman
``uretim.eklendi`` olayını yayınlar. Her mesaj log korelasyonu için ``tenant_slug_ctx``/
``request_id_ctx`` set eder. Hata izole edilir — döngü tek bozuk mesajla çökmez.

Dayanıklılık (S28, ADR-0047):
- **Veritabanı geçici yoksa mesaj düşürülmez:** bağlantı hataları geri çekilmeli yeniden denenir
  (``YENIDEN_DENEME_SN``); yazım ``olcum_id`` ile idempotent olduğundan tekrar güvenlidir. Kalıcı
  hatalar (bozuk veri, bilinmeyen tenant) eskisi gibi düşürülür.
- **Broker koparsa süreç ölmez:** bağlantı üstel geri çekilmeyle (en çok 30 sn) yeniden kurulur.
- **Kalıcı oturum + QoS 1:** sabit istemci kimliği ve ``clean_session=False`` ile işçi kapalıyken
  broker QoS 1 mesajları tutar; kenar ajanı da tamponundan yeniden gönderir (çift yazım yok).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
from uuid import uuid4

import aiomqtt
from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.context import request_id_ctx, tenant_slug_ctx
from app.core.db.tenancy import search_path_ayarla, tenant_bul
from app.core.gercekzaman import yayinla
from app.core.hata_izleme import hata_bildir, hata_izleme_kur
from app.core.logging import yapilandir_loglama
from app.core.metrikler import isci_sonuc, metrik_sunucusu_baslat
from app.ingestion.isleyici import MesajGecersiz, mesaj_coz
from app.ingestion.service import olcum_yaz_toplu

logger = logging.getLogger("app.ingestion.worker")

TOPIC = "fabrikaos/+/+/olcum"
ISCI = "ingestion"
ISTEMCI_KIMLIGI = "fabrikaos-ingestion"
YENIDEN_DENEME_SN: tuple[float, ...] = (0.5, 1, 2, 4, 8, 15)
GECICI_HATALAR: tuple[type[BaseException], ...] = (
    OperationalError,
    InterfaceError,
    ConnectionError,
    OSError,
    TimeoutError,
)


async def mesaj_ele(sm: async_sessionmaker[AsyncSession], topic: str, payload: bytes) -> None:
    """Tek MQTT mesajını işler. Bozuk/bilinmeyen → güvenle düşürür (asla yükseltmez)."""
    try:
        slug, cihaz_kod, paket = mesaj_coz(topic, payload)
    except MesajGecersiz:
        logger.warning("geçersiz mesaj düşürüldü: topic=%s", topic)
        isci_sonuc(ISCI, "dusuruldu")
        return

    t_slug = tenant_slug_ctx.set(slug)
    t_req = request_id_ctx.set(str(uuid4()))
    try:
        etkilenen: tuple[int, ...] = ()
        for deneme, bekle in enumerate((*YENIDEN_DENEME_SN, None)):
            try:
                async with sm() as session, session.begin():
                    tenant = await tenant_bul(session, slug)
                    if tenant is None or not tenant.aktif:
                        logger.warning("bilinmeyen/pasif tenant, düşürüldü: slug=%s", slug)
                        isci_sonuc(ISCI, "dusuruldu")
                        return
                    await search_path_ayarla(session, slug)
                    sonuc = await olcum_yaz_toplu(session, cihaz_kod=cihaz_kod, paketler=[paket])
                    etkilenen = sonuc.etkilenen_makineler
                break
            except GECICI_HATALAR:
                if bekle is None:
                    raise
                logger.warning(
                    "veritabanı geçici yok, yeniden denenecek (%d. deneme, %.1f sn): topic=%s",
                    deneme + 1,
                    bekle,
                    topic,
                )
                isci_sonuc(ISCI, "yeniden_deneme")
                await asyncio.sleep(bekle)
        for makine_id in etkilenen:
            await yayinla(slug, {"tur": "uretim.eklendi", "makine_id": makine_id, "kaynak": "saha"})
        isci_sonuc(ISCI, "islendi")
    except Exception as exc:  # noqa: BLE001 — tek mesaj döngüyü düşürmez
        logger.exception("ingestion mesaj işleme hatası: topic=%s", topic)
        isci_sonuc(ISCI, "hata")
        hata_bildir(exc)
    finally:
        tenant_slug_ctx.reset(t_slug)
        request_id_ctx.reset(t_req)


async def dinle(
    sm: async_sessionmaker[AsyncSession],
    *,
    broker_host: str,
    broker_port: int,
    dur: asyncio.Event | None = None,
    istemci_fabrikasi: type[aiomqtt.Client] = aiomqtt.Client,
) -> None:
    """Broker'a bağlanır; koparsa üstel geri çekilmeyle yeniden bağlanır (``dur`` verilene dek)."""
    bekle = 1.0
    while dur is None or not dur.is_set():
        try:
            async with istemci_fabrikasi(
                broker_host, port=broker_port, identifier=ISTEMCI_KIMLIGI, clean_session=False
            ) as client:
                await client.subscribe(TOPIC, qos=1)
                logger.info("broker'a bağlanıldı: %s:%s", broker_host, broker_port)
                bekle = 1.0
                async for message in client.messages:
                    await mesaj_ele(sm, str(message.topic), message.payload)
                    if dur is not None and dur.is_set():
                        return
        except aiomqtt.MqttError as exc:
            logger.warning("broker bağlantısı yok/koptu (%s); %.0f sn sonra yeniden", exc, bekle)
            isci_sonuc(ISCI, "baglanti_koptu")
            if dur is not None:
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(dur.wait(), timeout=bekle)
            else:
                await asyncio.sleep(bekle)
            bekle = min(bekle * 2, 30.0)


async def calistir(*, broker_host: str, broker_port: int, db_url: str) -> None:
    """MQTT'ye bağlanır ve süresiz dinler (kopmada kendiliğinden yeniden bağlanır)."""
    engine = create_async_engine(db_url, poolclass=NullPool)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    logger.info("ingestion worker başlıyor: broker=%s:%s", broker_host, broker_port)
    try:
        await dinle(sm, broker_host=broker_host, broker_port=broker_port)
    finally:
        await engine.dispose()


def main() -> None:
    s = get_settings()
    yapilandir_loglama(s.log_level)
    hata_izleme_kur(s)
    metrik_sunucusu_baslat(s.isci_metrik_portu)
    # aiomqtt/paho, Windows ProactorEventLoop'ta soket okuma/yazma kaydını desteklemez.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(calistir(broker_host=s.mqtt_host, broker_port=s.mqtt_port, db_url=s.database_url))


if __name__ == "__main__":
    main()
