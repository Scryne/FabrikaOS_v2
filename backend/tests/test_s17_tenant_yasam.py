"""S17 tenant yaşam döngüsü testleri — provizyon, plan değişimi, askıya alma, silme.

Kabul: panelden provizyonlanan tenant'a admin dakikalar içinde giriş yapar; askıya
alma erişimi ANINDA keser; silme yalnız onay=slug ile ve şemayı düşürür.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import PlatformDenetimIzi
from app.platform import service
from tests.conftest import TEST_URL
from tests.test_s17_platform_kimlik import (  # noqa: F401  (fixture'lar)
    oturum,
    platform_db,
    platform_giris,
)

TENANTLAR = "/api/v1/platform/tenantlar"


@pytest_asyncio.fixture(autouse=True)
async def platform_db_url() -> AsyncIterator[None]:
    """Provizyon/silme işleri test veritabanına gitsin (ayarlardaki dev DB'ye değil)."""
    service.db_url_ayarla(TEST_URL)
    yield
    service.db_url_ayarla(None)


async def _tenant_ac(
    istemci: AsyncClient, h: dict[str, str], slug: str, plan: str = "temel"
) -> dict:
    r = await istemci.post(
        TENANTLAR,
        json={
            "slug": slug,
            "ad": f"{slug.title()} Fabrika",
            "plan_kodu": plan,
            "admin_eposta": f"admin@{slug}.test",
            "admin_parola": "Parola12345!",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    return dict(r.json()["data"])


async def _tenant_giris(istemci: AsyncClient, slug: str) -> int:
    r = await istemci.post(
        "/api/v1/kimlik/token",
        data={"username": f"admin@{slug}.test", "password": "Parola12345!"},
        headers={"X-Tenant": slug},
    )
    return r.status_code


async def test_provizyon_ve_yeni_tenanta_giris(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    veri = await _tenant_ac(kurulu_istemci, h, "delta17")
    assert veri["slug"] == "delta17"
    assert veri["plan_kodu"] == "temel"
    assert veri["koltuk_kullanilan"] == 1  # provizyon admini

    # Kabul: yeni tenant'ın admini hemen giriş yapabilir.
    assert await _tenant_giris(kurulu_istemci, "delta17") == 200

    # Aynı slug ikinci kez → 409.
    r = await kurulu_istemci.post(
        TENANTLAR,
        json={
            "slug": "delta17",
            "ad": "Kopya",
            "plan_kodu": "temel",
            "admin_eposta": "x@delta17.test",
            "admin_parola": "Parola12345!",
        },
        headers=h,
    )
    assert r.status_code == 409


async def test_provizyon_dogrulamalari(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    govde = {
        "ad": "Test",
        "admin_eposta": "a@b.test",
        "admin_parola": "Parola12345!",
    }
    r = await kurulu_istemci.post(
        TENANTLAR, json={**govde, "slug": "Büyük_Harf", "plan_kodu": "temel"}, headers=h
    )
    assert r.status_code == 422  # geçersiz slug
    r = await kurulu_istemci.post(
        TENANTLAR, json={**govde, "slug": "gecerli17", "plan_kodu": "olmayan-plan"}, headers=h
    )
    assert r.status_code == 422  # katalog dışı plan


async def test_plan_degisimi_aninda_etkili(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    veri = await _tenant_ac(kurulu_istemci, h, "zeta17", plan="temel")

    # temel planda ai kapalı → tenant admini 403 MODUL_KAPALI alır.
    r = await kurulu_istemci.post(
        "/api/v1/kimlik/token",
        data={"username": "admin@zeta17.test", "password": "Parola12345!"},
        headers={"X-Tenant": "zeta17"},
    )
    th = {
        "X-Tenant": "zeta17",
        "Authorization": f"Bearer {r.json()['data']['access_token']}",
    }
    r = await kurulu_istemci.get("/api/v1/tahmin/modeller", headers=th)
    assert r.status_code == 403
    assert r.json()["hata_kodu"] == "MODUL_KAPALI"

    # Platformdan plan yükselt → bir SONRAKİ istekte açık (önbellek yok).
    r = await kurulu_istemci.patch(
        f"{TENANTLAR}/{veri['id']}", json={"plan_kodu": "kurumsal"}, headers=h
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["plan_kodu"] == "kurumsal"

    r = await kurulu_istemci.get("/api/v1/tahmin/modeller", headers=th)
    assert r.status_code == 200, r.text


async def test_askiya_alma_erisimi_keser_aktiflestirme_acar(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    veri = await _tenant_ac(kurulu_istemci, h, "eta17")
    assert await _tenant_giris(kurulu_istemci, "eta17") == 200

    r = await kurulu_istemci.post(f"{TENANTLAR}/{veri['id']}/askiya-al", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["aktif"] is False

    # Kabul: erişim ANINDA kesilir (giriş dahil her uç görünmez — 404).
    assert await _tenant_giris(kurulu_istemci, "eta17") == 404

    r = await kurulu_istemci.post(f"{TENANTLAR}/{veri['id']}/aktiflestir", headers=h)
    assert r.status_code == 200
    assert await _tenant_giris(kurulu_istemci, "eta17") == 200


async def test_silme_onay_ister_ve_semayi_dusurur(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
    oturum: AsyncSession,  # noqa: F811
) -> None:
    import asyncpg

    h = await platform_giris(kurulu_istemci)
    veri = await _tenant_ac(kurulu_istemci, h, "eps17")

    # Yanlış onay metni → 422, tenant durur.
    r = await kurulu_istemci.request(
        "DELETE", f"{TENANTLAR}/{veri['id']}", json={"onay": "yanlis"}, headers=h
    )
    assert r.status_code == 422
    assert await _tenant_giris(kurulu_istemci, "eps17") == 200

    # Doğru onay → silinir: giriş 404, şema yok, public kayıt yok.
    r = await kurulu_istemci.request(
        "DELETE", f"{TENANTLAR}/{veri['id']}", json={"onay": "eps17"}, headers=h
    )
    assert r.status_code == 200, r.text
    assert await _tenant_giris(kurulu_istemci, "eps17") == 404
    r = await kurulu_istemci.get(f"{TENANTLAR}/{veri['id']}", headers=h)
    assert r.status_code == 404

    conn = await asyncpg.connect(TEST_URL.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        sema_var = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name=$1)",
            "tenant_eps17",
        )
    finally:
        await conn.close()
    assert not sema_var


async def test_yasam_dongusu_denetim_izine_yazilir(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
    oturum: AsyncSession,  # noqa: F811
) -> None:
    h = await platform_giris(kurulu_istemci)
    await _tenant_ac(kurulu_istemci, h, "iota17")
    eylemler = (
        (
            await oturum.execute(
                select(PlatformDenetimIzi.eylem).where(PlatformDenetimIzi.kaynak == "tenant")
            )
        )
        .scalars()
        .all()
    )
    assert "provizyon" in eylemler
