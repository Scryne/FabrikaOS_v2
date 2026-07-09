"""S16 koltuk (seat) limiti testleri — `temel` plan koltuk=10, aşım 409 KOLTUK_LIMITI."""

from __future__ import annotations

import asyncpg
from httpx import AsyncClient

from app.control_plane.provizyon import tenant_provizyonla
from tests.conftest import TEST_URL
from tests.test_s16_entitlement import GAMMA, _giris

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
KULLANICILAR = "/api/v1/kullanicilar"


async def _aktif_sayisi() -> int:
    conn = await asyncpg.connect(_DSN)
    try:
        n = await conn.fetchval("SELECT count(*) FROM tenant_gamma16.kullanici WHERE aktif")
        return int(n)
    finally:
        await conn.close()


async def _kullanici_olustur(istemci: AsyncClient, h: dict[str, str], i: int) -> int:
    r = await istemci.post(
        KULLANICILAR,
        json={
            "eposta": f"koltuk{i}@gamma16.test",
            "parola": "Koltuk12345!",
            "ad_soyad": f"Koltuk {i}",
        },
        headers=h,
    )
    return r.status_code


async def test_koltuk_limiti_dolunca_409_pasiflesince_acilir(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    await tenant_provizyonla(
        slug=GAMMA["slug"],
        ad=GAMMA["ad"],
        admin_eposta=GAMMA["eposta"],
        admin_parola=GAMMA["parola"],
        plan_kodu="temel",
        db_url=TEST_URL,
    )
    h = await _giris(kurulu_istemci, GAMMA)

    # Limite kadar doldur (temel plan koltuk=10; mevcut aktifler + yeniler).
    mevcut = await _aktif_sayisi()
    for i in range(10 - mevcut):
        assert await _kullanici_olustur(kurulu_istemci, h, i) == 201
    assert await _aktif_sayisi() == 10

    # 11. aktif kullanıcı: 409 KOLTUK_LIMITI.
    r = await kurulu_istemci.post(
        KULLANICILAR,
        json={"eposta": "tasan@gamma16.test", "parola": "Koltuk12345!", "ad_soyad": "Taşan"},
        headers=h,
    )
    assert r.status_code == 409, r.text
    assert r.json()["hata_kodu"] == "KOLTUK_LIMITI"

    # Bir kullanıcı pasifleşince koltuk açılır (pasifler sayılmaz).
    conn = await asyncpg.connect(_DSN)
    try:
        await conn.execute(
            "UPDATE tenant_gamma16.kullanici SET aktif=false WHERE eposta='koltuk0@gamma16.test'"
        )
    finally:
        await conn.close()

    r = await kurulu_istemci.post(
        KULLANICILAR,
        json={"eposta": "tasan@gamma16.test", "parola": "Koltuk12345!", "ad_soyad": "Taşan"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert await _aktif_sayisi() == 10


async def test_sinirsiz_planda_limit_yok(test_db: str, kurulu_istemci: AsyncClient) -> None:
    """`kurumsal` plan koltuk sınırsız (None) — dolu tenant'ta bile oluşturma sürer."""
    conn = await asyncpg.connect(_DSN)
    try:
        tid = await conn.fetchval("SELECT id FROM public.tenant WHERE slug='gamma16'")
        await conn.execute(
            "UPDATE public.abonelik SET plan_kodu='kurumsal' WHERE tenant_id=$1", tid
        )
        h = await _giris(kurulu_istemci, GAMMA)
        r = await kurulu_istemci.post(
            KULLANICILAR,
            json={
                "eposta": "sinirsiz@gamma16.test",
                "parola": "Koltuk12345!",
                "ad_soyad": "Sınırsız",
            },
            headers=h,
        )
        assert r.status_code == 201, r.text
    finally:
        await conn.execute("UPDATE public.abonelik SET plan_kodu='temel' WHERE tenant_id=$1", tid)
        await conn.close()
