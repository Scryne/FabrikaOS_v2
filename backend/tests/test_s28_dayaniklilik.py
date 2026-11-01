"""S28 (ADR-0047): altyapı kesintisinde davranış — zarif bozulma, kurtarma, veri kaybı yok.

Üç kesinti: Redis (oran sınırı, refresh iptal listesi, gerçek-zaman yayını, hazırlık yoklaması),
nesne deposu (MinIO; belge sürümü) ve MQTT/veritabanı (alım işçisi). Kesinti, ilgili istemci
bozuk bir taklitle değiştirilerek üretilir; ardından gerçek istemciye dönülüp kurtarma sınanır.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import aiomqtt
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.core.security import ratelimit, redis_istemci
from app.ingestion import worker
from app.modules.dys import depolama
from app.modules.saha import repository as saha_repo
from app.modules.saha.models import Cihaz
from app.modules.uretim.models import Makine, UretimVerisi
from tests.conftest import ALFA

API = "/api/v1"


class BozukRedis:
    """Her çağrıda bağlantı hatası veren Redis (kesinti)."""

    def __getattr__(self, ad: str) -> Any:
        async def hata(*_a: object, **_k: object) -> None:
            raise ConnectionError("redis yok")

        return hata


@pytest.fixture
def redis_kesik() -> Iterator[None]:
    onceki = redis_istemci._redis
    redis_istemci.redis_ayarla(BozukRedis())  # type: ignore[arg-type]
    ratelimit._YEDEK.clear()
    yield
    redis_istemci.redis_ayarla(onceki)


async def _token(istemci: AsyncClient) -> dict[str, Any]:
    r = await istemci.post(
        f"{API}/kimlik/token",
        data={"username": ALFA["eposta"], "password": ALFA["parola"]},
        headers={"X-Tenant": ALFA["slug"]},
    )
    assert r.status_code == 200, r.text
    return dict(r.json()["data"])


# ── Redis ────────────────────────────────────────────────────────────────────


async def test_redis_kesintisinde_oran_siniri_yedege_gecer(redis_kesik: None) -> None:
    sonuclar = [
        (await ratelimit.rate_limit_kontrol("test:yedek", limit=3, pencere_sn=60)).izinli
        for _ in range(5)
    ]
    assert sonuclar == [True, True, True, False, False]  # koruma kalkmadı, giriş kilitlenmedi


async def test_redis_kesintisinde_giris_yazma_ve_saglik(
    kurulu_istemci: AsyncClient, redis_kesik: None
) -> None:
    tok = await _token(kurulu_istemci)  # giriş Redis'siz de çalışır
    h = {"X-Tenant": ALFA["slug"], "Authorization": f"Bearer {tok['access_token']}"}

    # Yazma yayın hatasına takılmaz; kayıt kalıcıdır.
    r = await kurulu_istemci.post(
        f"{API}/uygunsuzluklar",
        json={"baslik": f"Redis kesintisi {uuid.uuid4().hex[:6]}"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    uid = r.json()["data"]["id"]
    assert (await kurulu_istemci.get(f"{API}/uygunsuzluklar/{uid}", headers=h)).status_code == 200

    # Refresh: iptal listesi okunamıyor → güvenli tarafta 503 (500 değil).
    y = await kurulu_istemci.post(
        f"{API}/kimlik/yenile",
        json={"refresh_token": tok["refresh_token"]},
        headers={"X-Tenant": ALFA["slug"]},
    )
    assert y.status_code == 503, y.text
    assert y.json()["hata_kodu"] == "HIZMET_KULLANILAMAZ"

    hazir = await kurulu_istemci.get("/saglik/hazir")
    assert hazir.status_code == 503


async def test_redis_donunce_yenileme_calisir(kurulu_istemci: AsyncClient) -> None:
    tok = await _token(kurulu_istemci)
    y = await kurulu_istemci.post(
        f"{API}/kimlik/yenile",
        json={"refresh_token": tok["refresh_token"]},
        headers={"X-Tenant": ALFA["slug"]},
    )
    assert y.status_code == 200, y.text


# ── Nesne deposu ─────────────────────────────────────────────────────────────


class BozukDepo(depolama.BellekNesneDepo):
    def yukle(self, anahtar: str, veri: bytes, icerik_tipi: str) -> None:
        raise ConnectionError("minio yok")


async def test_depo_kesintisinde_surum_yarim_kalmaz(
    kurulu_istemci: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    tok = await _token(kurulu_istemci)
    h = {"X-Tenant": ALFA["slug"], "Authorization": f"Bearer {tok['access_token']}"}
    b = await kurulu_istemci.post(
        f"{API}/belgeler", json={"ad": "Kesinti prosedürü", "kategori": "prosedur"}, headers=h
    )
    assert b.status_code == 201, b.text
    bid = b.json()["data"]["id"]

    monkeypatch.setattr(depolama, "_depo", BozukDepo())
    r = await kurulu_istemci.post(
        f"{API}/belgeler/{bid}/surumler",
        files={"dosya": ("p.txt", b"icerik", "text/plain")},
        headers=h,
    )
    assert r.status_code == 503, r.text
    detay = (await kurulu_istemci.get(f"{API}/belgeler/{bid}", headers=h)).json()["data"]
    assert detay["guncel_surum"] == 0  # sürüm kaydı açılmadı

    monkeypatch.setattr(depolama, "_depo", depolama.BellekNesneDepo())  # depo döndü
    r = await kurulu_istemci.post(
        f"{API}/belgeler/{bid}/surumler",
        files={"dosya": ("p.txt", b"icerik", "text/plain")},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["surum_no"] == 1


# ── Alım işçisi: veritabanı ve broker kesintisi ──────────────────────────────


def _olcum(makine: str) -> tuple[str, bytes]:
    yuk = {
        "olcum_id": str(uuid.uuid4()),
        "makine_kod": makine,
        "zaman": datetime.now(UTC).isoformat(),
        "vardiya": "A",
        "planlanan_sure_dk": 60,
        "durus_sure_dk": 5,
        "toplam_adet": 100,
        "saglam_adet": 98,
        "ideal_cevrim_sn": 30,
    }
    return "fabrikaos/alfa/GW-DY/olcum", json.dumps(yuk).encode()


async def _hazirla(sm: async_sessionmaker[Any], makine: str) -> None:
    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        if await s.scalar(select(Cihaz).where(Cihaz.kod == "GW-DY")) is None:
            await saha_repo.cihaz_ekle(s, Cihaz(kod="GW-DY", ad="Dayanıklılık"))
        s.add(Makine(kod=makine, ad=makine))
        await s.commit()


async def _sayi(sm: async_sessionmaker[Any], makine: str) -> int:
    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        return int(
            await s.scalar(
                select(func.count())
                .select_from(UretimVerisi)
                .join(Makine, Makine.id == UretimVerisi.makine_id)
                .where(Makine.kod == makine)
            )
            or 0
        )


async def test_veritabani_gecici_yoksa_mesaj_dusmez(
    test_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    makine = f"MAK-DY-{uuid.uuid4().hex[:5]}"
    await _hazirla(sm, makine)
    monkeypatch.setattr(worker, "YENIDEN_DENEME_SN", (0, 0, 0))

    kalan_hata = 2

    def kesintili() -> Any:
        nonlocal kalan_hata
        if kalan_hata:
            kalan_hata -= 1
            raise OperationalError("SELECT 1", {}, ConnectionError("db yok"))
        return sm()

    topic, yuk = _olcum(makine)
    await worker.mesaj_ele(kesintili, topic, yuk)  # type: ignore[arg-type]
    assert await _sayi(sm, makine) == 1  # iki hata sonrası yazıldı, düşürülmedi
    await worker.mesaj_ele(sm, topic, yuk)  # aynı ölçüm yeniden gelirse: idempotent
    assert await _sayi(sm, makine) == 1


async def test_broker_koparsa_yeniden_baglanir(
    test_engine: AsyncEngine, monkeypatch: pytest.MonkeyPatch
) -> None:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    makine = f"MAK-BR-{uuid.uuid4().hex[:5]}"
    await _hazirla(sm, makine)
    topic, yuk = _olcum(makine)
    dur = asyncio.Event()
    baglanma: list[dict[str, Any]] = []

    class Mesaj:
        def __init__(self) -> None:
            self.topic, self.payload = topic, yuk

    class SahteIstemci:
        def __init__(self, host: str, **ayar: Any) -> None:
            baglanma.append(ayar)

        async def __aenter__(self) -> SahteIstemci:
            if len(baglanma) <= 2:
                raise aiomqtt.MqttError("broker yok")
            return self

        async def __aexit__(self, *_a: object) -> None:
            return None

        async def subscribe(self, _topic: str, qos: int = 0) -> None:
            assert qos == 1

        @property
        def messages(self) -> Any:
            async def akis() -> Any:
                yield Mesaj()
                dur.set()

            return akis()

    monkeypatch.setattr(asyncio, "sleep", _hizli_uyku)
    await asyncio.wait_for(
        worker.dinle(
            sm,
            broker_host="x",
            broker_port=1,
            dur=dur,
            istemci_fabrikasi=SahteIstemci,  # type: ignore[arg-type]
        ),
        timeout=10,
    )
    assert len(baglanma) == 3  # iki başarısız deneme, üçüncüde bağlandı
    assert all(a["clean_session"] is False and a["identifier"] for a in baglanma)
    assert await _sayi(sm, makine) == 1


_gercek_uyku = asyncio.sleep


async def _hizli_uyku(_sn: float, *a: Any, **k: Any) -> None:
    await _gercek_uyku(0)
