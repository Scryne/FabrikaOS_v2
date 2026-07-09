"""S16 entitlement zorlama testleri.

Kabul kriterleri: kapalı modüle erişim 403 ``MODUL_KAPALI`` (admin bile — bypass yok),
değişiklik ANINDA etkili, tenant izolasyonu, çekirdek uçlar entitlement dışı.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.control_plane import entitlement_service
from app.control_plane.models import Tenant
from app.control_plane.provizyon import tenant_provizyonla
from tests.conftest import ALFA, BETA, TEST_URL

GAMMA = {
    "slug": "gamma16",
    "ad": "Gamma Temel Fabrika",
    "eposta": "admin@gamma16.test",
    "parola": "Gamma12345!",
}


async def _giris(istemci: AsyncClient, t: dict) -> dict[str, str]:
    r = await istemci.post(
        "/api/v1/kimlik/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return {
        "X-Tenant": t["slug"],
        "Authorization": f"Bearer {r.json()['data']['access_token']}",
    }


@pytest_asyncio.fixture
async def gamma_db(test_db: str) -> None:
    """`temel` planlı üçüncü tenant (idempotent — modül başına bir kez iş yapar)."""
    await tenant_provizyonla(
        slug=GAMMA["slug"],
        ad=GAMMA["ad"],
        admin_eposta=GAMMA["eposta"],
        admin_parola=GAMMA["parola"],
        plan_kodu="temel",
        db_url=TEST_URL,
    )


@pytest_asyncio.fixture
async def oturum(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as s:
        yield s


async def _tenant_id(oturum: AsyncSession, slug: str) -> int:
    tid = (await oturum.execute(select(Tenant.id).where(Tenant.slug == slug))).scalar_one()
    return int(tid)


async def test_temel_planda_kapali_moduller_403_acik_moduller_200(
    gamma_db: None, kurulu_istemci: AsyncClient
) -> None:
    h = await _giris(kurulu_istemci, GAMMA)

    # Açık modüller (temel: uretim/isemri/bakim/stok) çalışır.
    for yol in ("/api/v1/makineler", "/api/v1/is-emirleri", "/api/v1/malzemeler"):
        r = await kurulu_istemci.get(yol, headers=h)
        assert r.status_code == 200, f"{yol}: {r.text}"

    # Kapalı modüller: admin TÜM RBAC izinlerine sahip olsa da 403 (bypass yok).
    for yol in (
        "/api/v1/tahmin/modeller",
        "/api/v1/analitik/kpi",
        "/api/v1/raporlar",
        "/api/v1/firmalar",
        "/api/v1/kalite-kontrolleri",
    ):
        r = await kurulu_istemci.get(yol, headers=h)
        assert r.status_code == 403, f"{yol}: {r.status_code} {r.text}"
        assert r.json()["hata_kodu"] == "MODUL_KAPALI", yol


async def test_cekirdek_uclar_entitlement_disi(gamma_db: None, kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, GAMMA)
    for yol in ("/api/v1/kimlik/ben", "/api/v1/kullanicilar", "/api/v1/roller"):
        r = await kurulu_istemci.get(yol, headers=h)
        assert r.status_code == 200, f"{yol}: {r.text}"


async def test_override_aninda_etkili_ve_kaldirilinca_plana_doner(
    kurulu_istemci: AsyncClient, oturum: AsyncSession
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    alfa_id = await _tenant_id(oturum, "alfa")

    r = await kurulu_istemci.get("/api/v1/tahmin/modeller", headers=h)
    assert r.status_code == 200, r.text  # deneme planında ai açık

    try:
        await entitlement_service.modul_hakki_ayarla(oturum, alfa_id, "ai", False)
        await oturum.commit()

        # Sunucu yeniden başlatılmadan, bir SONRAKİ istekte kapalı (önbellek yok).
        r = await kurulu_istemci.get("/api/v1/tahmin/modeller", headers=h)
        assert r.status_code == 403
        assert r.json()["hata_kodu"] == "MODUL_KAPALI"
    finally:
        await entitlement_service.modul_hakki_ayarla(oturum, alfa_id, "ai", None)
        await oturum.commit()

    r = await kurulu_istemci.get("/api/v1/tahmin/modeller", headers=h)
    assert r.status_code == 200, r.text  # override kalktı → plana döndü


async def test_override_tenant_izoledir(
    kurulu_istemci: AsyncClient, oturum: AsyncSession
) -> None:
    alfa_id = await _tenant_id(oturum, "alfa")
    try:
        await entitlement_service.modul_hakki_ayarla(oturum, alfa_id, "ai", False)
        await oturum.commit()

        beta_h = await _giris(kurulu_istemci, BETA)
        r = await kurulu_istemci.get("/api/v1/tahmin/modeller", headers=beta_h)
        assert r.status_code == 200, r.text  # alfa'nın hakkı beta'yı etkilemez
    finally:
        await entitlement_service.modul_hakki_ayarla(oturum, alfa_id, "ai", None)
        await oturum.commit()


async def test_katalog_disi_kod_reddedilir(oturum: AsyncSession) -> None:
    with pytest.raises(ValueError, match="Katalogda olmayan modül"):
        await entitlement_service.modul_hakki_ayarla(oturum, 1, "olmayan-modul", True)
    with pytest.raises(ValueError, match="Katalogda olmayan özellik"):
        await entitlement_service.ozellik_bayragi_ayarla(oturum, 1, "olmayan-ozellik", True)


async def test_ozellik_bayragi_override_servisi(
    oturum: AsyncSession, test_db: str
) -> None:
    alfa_id = await _tenant_id(oturum, "alfa")
    tenant = (
        await oturum.execute(select(Tenant).where(Tenant.id == alfa_id))
    ).scalar_one()

    once = await entitlement_service.tenant_etkin_ozellikler(oturum, tenant)
    assert once["mobil-api"] is True  # deneme planı tüm özellikleri açar

    try:
        await entitlement_service.ozellik_bayragi_ayarla(oturum, alfa_id, "mobil-api", False)
        await oturum.commit()
        sonra = await entitlement_service.tenant_etkin_ozellikler(oturum, tenant)
        assert sonra["mobil-api"] is False
    finally:
        await entitlement_service.ozellik_bayragi_ayarla(oturum, alfa_id, "mobil-api", None)
        await oturum.commit()
