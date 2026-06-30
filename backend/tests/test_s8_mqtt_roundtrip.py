"""S8 uçtan uca: gerçek broker → worker mesaj_ele → tenant şeması.

Mosquitto'yu testcontainers ile kaldırır. Docker yoksa testi atlar (DoD'u broker'sız
testler zaten karşılar).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime

import fakeredis.aioredis
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.core.security import redis_istemci
from app.modules.saha import repository
from app.modules.saha.models import Cihaz
from app.modules.uretim.models import Makine, UretimVerisi

pytestmark = pytest.mark.asyncio

pytest.importorskip("testcontainers.core.container")


@pytest.fixture(scope="module")
def mosquitto() -> Iterator[tuple[str, int]]:
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.waiting_utils import wait_for_logs

    c = (
        DockerContainer("eclipse-mosquitto:2")
        .with_exposed_ports(1883)
        .with_command(
            'sh -c \'printf "listener 1883\\nallow_anonymous true\\n" > /m.conf '
            "&& mosquitto -c /m.conf'"
        )
    )
    try:
        c.start()
    except Exception as exc:  # noqa: BLE001 — Docker yoksa atla
        pytest.skip(f"Docker/mosquitto yok: {exc}")
    wait_for_logs(c, "mosquitto version 2", timeout=30)
    yield c.get_container_host_ip(), int(c.get_exposed_port(1883))
    c.stop()


@pytest.fixture(autouse=True)
def _fake_redis() -> Iterator[None]:
    redis_istemci.redis_ayarla(fakeredis.aioredis.FakeRedis(decode_responses=True))
    yield
    redis_istemci.redis_ayarla(None)


async def test_edge_to_worker_roundtrip(test_engine: object, mosquitto: tuple[str, int]) -> None:
    import aiomqtt

    from app.ingestion.worker import mesaj_ele

    host, port = mosquitto
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[arg-type]
    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        await repository.cihaz_ekle(s, Cihaz(kod="GW-RT", ad="RT"))
        s.add(Makine(kod="MAK-RT", ad="RT"))
        await s.commit()

    payload = json.dumps(
        {
            "olcum_id": str(uuid.uuid4()),
            "makine_kod": "MAK-RT",
            "zaman": datetime.now(UTC).isoformat(),
            "vardiya": "A",
            "planlanan_sure_dk": 60,
            "durus_sure_dk": 5,
            "toplam_adet": 100,
            "saglam_adet": 98,
            "ideal_cevrim_sn": 30,
        }
    )
    topic = "fabrikaos/alfa/GW-RT/olcum"
    async with aiomqtt.Client(host, port=port) as pub:
        await pub.subscribe(topic)
        await pub.publish(topic, payload.encode(), qos=1)
        async for m in pub.messages:
            await mesaj_ele(sm, str(m.topic), m.payload)
            break

    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        sayi = await s.scalar(
            select(func.count())
            .select_from(UretimVerisi)
            .join(Makine, Makine.id == UretimVerisi.makine_id)
            .where(Makine.kod == "MAK-RT")
        )
        assert sayi == 1
