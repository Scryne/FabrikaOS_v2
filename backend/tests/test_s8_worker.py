"""S8 worker birim testi: mesaj_ele tek mesajı doğru tenant şemasına yazar (broker'sız).

MQTT round-trip (gerçek broker) testi Task 13'te testcontainers ile eklenir.
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
from app.ingestion.worker import mesaj_ele
from app.modules.saha import repository
from app.modules.saha.models import Cihaz
from app.modules.uretim.models import Makine, UretimVerisi

pytestmark = pytest.mark.asyncio


def _payload(makine_kod: str) -> bytes:
    return json.dumps(
        {
            "olcum_id": str(uuid.uuid4()),
            "makine_kod": makine_kod,
            "zaman": datetime.now(UTC).isoformat(),
            "vardiya": "A",
            "planlanan_sure_dk": 60,
            "durus_sure_dk": 5,
            "toplam_adet": 100,
            "saglam_adet": 98,
            "ideal_cevrim_sn": 30,
        }
    ).encode()


@pytest.fixture(autouse=True)
def _fake_redis() -> Iterator[None]:
    redis_istemci.redis_ayarla(fakeredis.aioredis.FakeRedis(decode_responses=True))
    yield
    redis_istemci.redis_ayarla(None)


async def test_mesaj_ele_yazar(test_engine: object) -> None:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[arg-type]
    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        await repository.cihaz_ekle(s, Cihaz(kod="GW-WRK", ad="WRK"))
        s.add(Makine(kod="MAK-WRK", ad="WRK"))
        await s.commit()

    await mesaj_ele(sm, "fabrikaos/alfa/GW-WRK/olcum", _payload("MAK-WRK"))

    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        sayi = await s.scalar(
            select(func.count())
            .select_from(UretimVerisi)
            .join(Makine, Makine.id == UretimVerisi.makine_id)
            .where(Makine.kod == "MAK-WRK")
        )
        assert sayi == 1


async def test_mesaj_ele_bozuk_topic_dusurur(test_engine: object) -> None:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[arg-type]
    # Hata fırlatmamalı (güvenle düşürülür)
    await mesaj_ele(sm, "bozuk/topic", b"{}")


async def test_mesaj_ele_bilinmeyen_tenant_dusurur(test_engine: object) -> None:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[arg-type]
    await mesaj_ele(sm, "fabrikaos/yokboyletenant/GW/olcum", _payload("MAK-WRK"))
