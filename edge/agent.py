"""Edge ajanı: oku → özetle → tampona yaz → (bağlıysa) yayınla. Graceful shutdown.

Çalıştırma: ``python -m edge.agent``. Sürücü ham sayaçları verir; önceki okumayla
fark alınıp aralık özeti tampona yazılır; ardından bekleyenler MQTT'ye yayınlanır.
Broker yoksa paketler tamponda kalır (store-and-forward) ve sonraki döngüde gönderilir.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
import sys

import aiomqtt

from edge.ayar import EdgeAyar
from edge.ozetleyici import ozetle
from edge.paket import HamOkuma
from edge.suruculer import SahaSurucu
from edge.suruculer.modbus import ModbusSurucu
from edge.suruculer.opcua import OpcUaSurucu
from edge.suruculer.simulasyon import SimulasyonSurucu
from edge.tampon import Tampon
from edge.yayinci import yayinla_bekleyenler

logger = logging.getLogger("edge.agent")


def surucu_yap(ayar: EdgeAyar) -> SahaSurucu:
    if ayar.surucu == "simulasyon":
        return SimulasyonSurucu(ayar.makine_kodlari, tohum=ayar.tohum)
    if ayar.surucu == "opcua":
        return OpcUaSurucu()
    if ayar.surucu == "modbus":
        return ModbusSurucu()
    raise ValueError(f"Bilinmeyen sürücü: {ayar.surucu!r}")


def dongu_adimi(
    surucu: SahaSurucu, tampon: Tampon, onceki: dict[str, HamOkuma]
) -> dict[str, HamOkuma]:
    """Bir okuma döngüsü: yeni okumaları al, önceki varsa özetle ve tampona ekle."""
    for okuma in surucu.oku():
        gecmis = onceki.get(okuma.makine_kod)
        if gecmis is not None:
            paket = ozetle(gecmis, okuma)
            if paket.toplam_adet > 0 or paket.durus_sure_dk > 0:
                tampon.ekle(str(paket.olcum_id), paket.model_dump_json())
        onceki[okuma.makine_kod] = okuma
    return onceki


async def calistir(ayar: EdgeAyar, *, dur: asyncio.Event) -> None:
    surucu = surucu_yap(ayar)
    tampon = Tampon(ayar.tampon_yolu)
    onceki: dict[str, HamOkuma] = {}
    logger.info("edge ajanı başladı: cihaz=%s tenant=%s", ayar.cihaz_kod, ayar.tenant_slug)
    while not dur.is_set():
        onceki = dongu_adimi(surucu, tampon, onceki)
        with contextlib.suppress(aiomqtt.MqttError):
            async with aiomqtt.Client(ayar.broker_host, port=ayar.broker_port) as client:
                gonderilen = await yayinla_bekleyenler(
                    client, tampon, slug=ayar.tenant_slug, cihaz_kod=ayar.cihaz_kod
                )
                if gonderilen:
                    logger.info("%d ölçüm yayınlandı", gonderilen)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(dur.wait(), timeout=ayar.aralik_sn)
    bekleyen = tampon.bekleyen_sayisi()
    tampon.kapat()
    logger.info("edge ajanı durdu (%d bekleyen tamponda)", bekleyen)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # aiomqtt/paho, Windows ProactorEventLoop'ta soket okuma/yazma kaydını desteklemez.
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    ayar = EdgeAyar()
    dur = asyncio.Event()

    async def _ana() -> None:
        loop = asyncio.get_running_loop()
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(signal.SIGINT, dur.set)
            loop.add_signal_handler(signal.SIGTERM, dur.set)
        await calistir(ayar, dur=dur)

    asyncio.run(_ana())


if __name__ == "__main__":
    main()
