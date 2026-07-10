"""S17 KVKK ihraç testleri — 202 + arka plan ZIP + indirme.

Kabul: ihraç ZIP'i tenant verisini eksiksiz içerir (bilinen kullanıcı e-postası
``tenant/kullanici.json``'da; tablolar manifest'te); hazır değilken indirme 409;
indirme baytları depodaki artefaktla birebir aynı.
"""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.control_plane.models import PlatformDenetimIzi, TenantIhrac
from app.modules.dys.depolama import BellekNesneDepo, nesne_depo_ayarla
from app.platform import ihrac
from tests.conftest import ALFA
from tests.test_s17_platform_kimlik import (  # noqa: F401  (fixture'lar)
    oturum,
    platform_db,
    platform_giris,
)

TENANTLAR = "/api/v1/platform/tenantlar"
IHRACLAR = "/api/v1/platform/ihraclar"


@pytest_asyncio.fixture
async def ihrac_ortami(test_engine: AsyncEngine) -> AsyncIterator[BellekNesneDepo]:
    """Arka plan görevini test motoruna + bellek deposuna bağlar, es-zamanlı koşturur."""
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[var-annotated]
    ihrac.oturum_fabrikasi_ayarla(sm)
    ihrac.es_zamanli_ayarla(True)
    depo = BellekNesneDepo()
    nesne_depo_ayarla(depo)
    try:
        yield depo
    finally:
        ihrac.oturum_fabrikasi_ayarla(None)
        ihrac.es_zamanli_ayarla(False)
        nesne_depo_ayarla(None)


async def _alfa_id(istemci: AsyncClient, h: dict[str, str]) -> int:
    r = await istemci.get(TENANTLAR, params={"arama": "alfa"}, headers=h)
    return int(r.json()["data"][0]["id"])


async def test_ihrac_uctan_uca_zip_icerigi_ve_indirme(
    platform_db: None,  # noqa: F811
    ihrac_ortami: BellekNesneDepo,
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    alfa_id = await _alfa_id(kurulu_istemci, h)

    r = await kurulu_istemci.post(f"{TENANTLAR}/{alfa_id}/ihrac", headers=h)
    assert r.status_code == 202, r.text
    ihrac_id = r.json()["data"]["id"]
    assert r.json()["data"]["durum"] == "kuyrukta"  # anlık görüntü

    # es-zamanlı görev bitti → listede hazir.
    r = await kurulu_istemci.get(IHRACLAR, params={"tenant_id": alfa_id}, headers=h)
    kayit = next(k for k in r.json()["data"] if k["id"] == ihrac_id)
    assert kayit["durum"] == "hazir", kayit
    assert kayit["tablo_sayisi"] > 10  # tenant şemasındaki tüm modül tabloları
    assert kayit["boyut"] > 0

    # İndir → ZIP açılır, bilinen veriler içinde.
    r = await kurulu_istemci.get(f"{IHRACLAR}/{ihrac_id}/indir", headers=h)
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    z = zipfile.ZipFile(io.BytesIO(r.content))
    adlar = set(z.namelist())
    assert {"manifest.json", "public/tenant.json", "tenant/kullanici.json"} <= adlar

    kullanicilar = json.loads(z.read("tenant/kullanici.json"))
    assert any(k["eposta"] == ALFA["eposta"] for k in kullanicilar)  # KVKK eksiksizlik
    tenantlar = json.loads(z.read("public/tenant.json"))
    assert tenantlar[0]["slug"] == "alfa"
    manifest = json.loads(z.read("manifest.json"))
    assert manifest["slug"] == "alfa"
    assert manifest["tenant_tablolari"]["kullanici"] >= 1

    # Bayt düzeyi eşleşme: indirilen içerik depodaki artefaktın aynısı.
    anahtar = ihrac.ihrac_nesne_anahtari("alfa", ihrac_id)
    assert ihrac_ortami.indir(anahtar) == r.content


async def test_hazir_olmayan_ihrac_indirilemez_409(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
    oturum: AsyncSession,  # noqa: F811
) -> None:
    h = await platform_giris(kurulu_istemci)
    alfa_id = await _alfa_id(kurulu_istemci, h)
    kayit = TenantIhrac(tenant_id=alfa_id, slug="alfa")  # kuyrukta
    oturum.add(kayit)
    await oturum.commit()

    r = await kurulu_istemci.get(f"{IHRACLAR}/{kayit.id}/indir", headers=h)
    assert r.status_code == 409
    r = await kurulu_istemci.get(f"{IHRACLAR}/999999/indir", headers=h)
    assert r.status_code == 404


async def test_olmayan_tenant_ihraci_404(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    r = await kurulu_istemci.post(f"{TENANTLAR}/999999/ihrac", headers=h)
    assert r.status_code == 404


async def test_ihrac_denetim_izinde(
    platform_db: None,  # noqa: F811
    ihrac_ortami: BellekNesneDepo,
    kurulu_istemci: AsyncClient,
    oturum: AsyncSession,  # noqa: F811
) -> None:
    h = await platform_giris(kurulu_istemci)
    alfa_id = await _alfa_id(kurulu_istemci, h)
    await kurulu_istemci.post(f"{TENANTLAR}/{alfa_id}/ihrac", headers=h)
    eylemler = (
        (
            await oturum.execute(
                select(PlatformDenetimIzi.eylem).where(
                    PlatformDenetimIzi.kaynak == "tenant",
                    PlatformDenetimIzi.kaynak_id == str(alfa_id),
                )
            )
        )
        .scalars()
        .all()
    )
    assert "ihrac" in eylemler
