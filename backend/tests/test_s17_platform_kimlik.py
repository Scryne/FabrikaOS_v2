"""S17 platform kimlik testleri — düzlem ayrımı + rotasyon + denetim izi.

Kabul: tenant admin token'ı platform uçlarında 401; platform token'ı tenant
uçlarında 401; refresh rotasyonlu (eski jti tekrar kullanılamaz).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.control_plane.models import PlatformDenetimIzi
from app.platform.kimlik_service import platform_yonetici_olustur
from tests.conftest import ALFA
from tests.test_s16_entitlement import _giris

KOK = {"eposta": "root@fabrikaos.test", "parola": "Platform12345!"}
TOKEN = "/api/v1/platform/kimlik/token"
BEN = "/api/v1/platform/kimlik/ben"


@pytest_asyncio.fixture
async def oturum(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as s:
        yield s


@pytest_asyncio.fixture
async def platform_db(oturum: AsyncSession, test_db: str) -> None:
    """Kök platform yöneticisi (idempotent upsert)."""
    await platform_yonetici_olustur(
        oturum, eposta=KOK["eposta"], parola=KOK["parola"], ad_soyad="Kök Yönetici"
    )
    await oturum.commit()


async def platform_giris(istemci: AsyncClient) -> dict[str, str]:
    r = await istemci.post(TOKEN, data={"username": KOK["eposta"], "password": KOK["parola"]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def test_giris_ve_ben(platform_db: None, kurulu_istemci: AsyncClient) -> None:
    h = await platform_giris(kurulu_istemci)
    r = await kurulu_istemci.get(BEN, headers=h)  # X-Tenant başlığı YOK
    assert r.status_code == 200, r.text
    assert r.json()["data"]["eposta"] == KOK["eposta"]


async def test_yanlis_parola_401(platform_db: None, kurulu_istemci: AsyncClient) -> None:
    r = await kurulu_istemci.post(
        TOKEN, data={"username": KOK["eposta"], "password": "yanlis-parola"}
    )
    assert r.status_code == 401


async def test_kimliksiz_401(platform_db: None, kurulu_istemci: AsyncClient) -> None:
    r = await kurulu_istemci.get(BEN)
    assert r.status_code == 401


async def test_tenant_tokeni_platform_ucunda_401(
    platform_db: None, kurulu_istemci: AsyncClient
) -> None:
    tenant_h = await _giris(kurulu_istemci, ALFA)  # tüm izinli tenant admin'i
    r = await kurulu_istemci.get(BEN, headers={"Authorization": tenant_h["Authorization"]})
    assert r.status_code == 401  # tip uyuşmazlığı: access != platform_access


async def test_platform_tokeni_tenant_ucunda_401(
    platform_db: None, kurulu_istemci: AsyncClient
) -> None:
    h = await platform_giris(kurulu_istemci)
    r = await kurulu_istemci.get("/api/v1/kimlik/ben", headers={**h, "X-Tenant": ALFA["slug"]})
    assert r.status_code == 401  # tip uyuşmazlığı: platform_access != access


async def test_yenile_rotasyonu_eski_refresh_iptal(
    platform_db: None, kurulu_istemci: AsyncClient
) -> None:
    r = await kurulu_istemci.post(
        TOKEN, data={"username": KOK["eposta"], "password": KOK["parola"]}
    )
    eski_refresh = r.json()["data"]["refresh_token"]

    r = await kurulu_istemci.post(
        "/api/v1/platform/kimlik/yenile", json={"refresh_token": eski_refresh}
    )
    assert r.status_code == 200, r.text
    yeni = r.json()["data"]
    assert yeni["refresh_token"] != eski_refresh

    # Rotasyon: eski refresh yeniden kullanılamaz.
    r = await kurulu_istemci.post(
        "/api/v1/platform/kimlik/yenile", json={"refresh_token": eski_refresh}
    )
    assert r.status_code == 401

    # Yeni access geçerli.
    r = await kurulu_istemci.get(BEN, headers={"Authorization": f"Bearer {yeni['access_token']}"})
    assert r.status_code == 200


async def test_cikis_refresh_iptal_eder(platform_db: None, kurulu_istemci: AsyncClient) -> None:
    r = await kurulu_istemci.post(
        TOKEN, data={"username": KOK["eposta"], "password": KOK["parola"]}
    )
    veri = r.json()["data"]
    h = {"Authorization": f"Bearer {veri['access_token']}"}

    r = await kurulu_istemci.post(
        "/api/v1/platform/kimlik/cikis", json={"refresh_token": veri["refresh_token"]}, headers=h
    )
    assert r.status_code == 200

    r = await kurulu_istemci.post(
        "/api/v1/platform/kimlik/yenile", json={"refresh_token": veri["refresh_token"]}
    )
    assert r.status_code == 401


async def test_giris_platform_denetim_izine_yazilir(
    platform_db: None, kurulu_istemci: AsyncClient, oturum: AsyncSession
) -> None:
    await platform_giris(kurulu_istemci)
    kayitlar = (
        (
            await oturum.execute(
                select(PlatformDenetimIzi).where(
                    PlatformDenetimIzi.kaynak == "platform_kimlik",
                    PlatformDenetimIzi.eylem == "giris",
                    PlatformDenetimIzi.yonetici_eposta == KOK["eposta"],
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(kayitlar) >= 1
