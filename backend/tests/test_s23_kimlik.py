"""S23 kimlik sertleştirme API testleri — 2FA akışı, oturum yönetimi, parola politikası,
IP izin listesi, tenant 2FA zorunluluğu."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.security.totp import kod_uret
from tests.conftest import ALFA
from tests.test_s16_entitlement import _giris

pytestmark = pytest.mark.asyncio

KIMLIK = "/api/v1/kimlik"


async def _guvenlik_ayarla(engine: AsyncEngine, slug: str, ayarlar: dict[str, Any] | None) -> None:
    sm = async_sessionmaker(engine, expire_on_commit=False)
    async with sm() as db:
        await db.execute(
            text("UPDATE public.tenant SET guvenlik_ayarlari = CAST(:a AS jsonb) WHERE slug = :s"),
            {"a": "null" if ayarlar is None else __import__("json").dumps(ayarlar), "s": slug},
        )
        await db.commit()


@pytest_asyncio.fixture
async def temiz_guvenlik(test_engine: AsyncEngine) -> AsyncIterator[AsyncEngine]:
    """Test sonunda alfa güvenlik ayarlarını sıfırlar (testler arası sızıntı olmasın)."""
    try:
        yield test_engine
    finally:
        await _guvenlik_ayarla(test_engine, "alfa", None)


async def _kullanici_ac(
    istemci: AsyncClient, h: dict[str, str], *, parola: str = "Deneme12345!"
) -> str:
    eposta = f"s23-{uuid.uuid4().hex[:8]}@alfa.test"
    r = await istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": eposta, "parola": parola, "ad_soyad": "S23", "roller": ["izleyici"]},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return eposta


async def test_2fa_kurulum_giris_kurtarma_ve_kapatma(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    admin_h = await _giris(kurulu_istemci, ALFA)
    eposta = await _kullanici_ac(kurulu_istemci, admin_h)
    h = await _giris(kurulu_istemci, {"slug": "alfa", "eposta": eposta, "parola": "Deneme12345!"})

    # Kurulum: sır + URI → kodla etkinleştir → kurtarma kodları BİR KEZ döner.
    r = await kurulu_istemci.post(f"{KIMLIK}/2fa-kur", headers=h)
    assert r.status_code == 200, r.text
    sir = r.json()["data"]["sir"]
    assert r.json()["data"]["otpauth_uri"].startswith("otpauth://totp/")
    r = await kurulu_istemci.post(f"{KIMLIK}/2fa-etkinlestir", json={"kod": "000000"}, headers=h)
    assert r.status_code == 422  # yanlış kod etkinleştirmez
    r = await kurulu_istemci.post(
        f"{KIMLIK}/2fa-etkinlestir", json={"kod": kod_uret(sir)}, headers=h
    )
    assert r.status_code == 200, r.text
    kurtarma = r.json()["data"]["kurtarma_kodlari"]
    assert len(kurtarma) == 8

    # /ben artık 2FA aktif der.
    r = await kurulu_istemci.get(f"{KIMLIK}/ben", headers=h)
    assert r.json()["data"]["iki_asama_aktif"] is True

    # Girişte parola yetmez: geçici token döner, access boştur.
    r = await kurulu_istemci.post(
        f"{KIMLIK}/token",
        data={"username": eposta, "password": "Deneme12345!"},
        headers={"X-Tenant": "alfa"},
    )
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["iki_asama_gerekli"] is True and veri["access_token"] == ""
    gecici = veri["gecici_token"]

    # Yanlış kod reddi.
    r = await kurulu_istemci.post(
        f"{KIMLIK}/2fa-dogrula",
        json={"gecici_token": gecici, "kod": "000000"},
        headers={"X-Tenant": "alfa"},
    )
    assert r.status_code == 401

    # Doğru TOTP → tam çift; geçici token TEK kullanımlıktır.
    r = await kurulu_istemci.post(
        f"{KIMLIK}/2fa-dogrula",
        json={"gecici_token": gecici, "kod": kod_uret(sir)},
        headers={"X-Tenant": "alfa"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["access_token"]
    r = await kurulu_istemci.post(
        f"{KIMLIK}/2fa-dogrula",
        json={"gecici_token": gecici, "kod": kod_uret(sir)},
        headers={"X-Tenant": "alfa"},
    )
    assert r.status_code == 401  # tekrar oynatma (replay) engellenir

    # Kurtarma koduyla giriş — kod bir kez kullanılır.
    r = await kurulu_istemci.post(
        f"{KIMLIK}/token",
        data={"username": eposta, "password": "Deneme12345!"},
        headers={"X-Tenant": "alfa"},
    )
    gecici2 = r.json()["data"]["gecici_token"]
    r = await kurulu_istemci.post(
        f"{KIMLIK}/2fa-dogrula",
        json={"gecici_token": gecici2, "kod": kurtarma[0]},
        headers={"X-Tenant": "alfa"},
    )
    assert r.status_code == 200, r.text
    yeni_access = r.json()["data"]["access_token"]
    r = await kurulu_istemci.post(
        f"{KIMLIK}/token",
        data={"username": eposta, "password": "Deneme12345!"},
        headers={"X-Tenant": "alfa"},
    )
    gecici3 = r.json()["data"]["gecici_token"]
    r = await kurulu_istemci.post(
        f"{KIMLIK}/2fa-dogrula",
        json={"gecici_token": gecici3, "kod": kurtarma[0]},
        headers={"X-Tenant": "alfa"},
    )
    assert r.status_code == 401  # aynı kurtarma kodu ikinci kez geçmez

    # Kapatma: parola + geçerli kod → sonraki giriş yine tek adım.
    h2 = {"X-Tenant": "alfa", "Authorization": f"Bearer {yeni_access}"}
    r = await kurulu_istemci.post(
        f"{KIMLIK}/2fa-kapat",
        json={"parola": "Deneme12345!", "kod": kod_uret(sir)},
        headers=h2,
    )
    assert r.status_code == 200, r.text
    r = await kurulu_istemci.post(
        f"{KIMLIK}/token",
        data={"username": eposta, "password": "Deneme12345!"},
        headers={"X-Tenant": "alfa"},
    )
    assert r.json()["data"]["access_token"] and not r.json()["data"]["iki_asama_gerekli"]


async def test_oturum_listesi_ve_uzaktan_sonlandirma(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    admin_h = await _giris(kurulu_istemci, ALFA)
    eposta = await _kullanici_ac(kurulu_istemci, admin_h)

    r = await kurulu_istemci.post(
        f"{KIMLIK}/token",
        data={"username": eposta, "password": "Deneme12345!"},
        headers={"X-Tenant": "alfa"},
    )
    veri = r.json()["data"]
    h = {"X-Tenant": "alfa", "Authorization": f"Bearer {veri['access_token']}"}
    refresh = veri["refresh_token"]

    r = await kurulu_istemci.get(f"{KIMLIK}/oturumlar", headers=h)
    assert r.status_code == 200, r.text
    oturumlar = r.json()["data"]
    assert len(oturumlar) >= 1
    oturum_id = oturumlar[0]["id"]
    assert "jti" not in oturumlar[0]  # sır sızdırılmaz

    # Uzaktan sonlandır → o refresh artık yenilenemez.
    r = await kurulu_istemci.delete(f"{KIMLIK}/oturumlar/{oturum_id}", headers=h)
    assert r.status_code == 200, r.text
    r = await kurulu_istemci.post(
        f"{KIMLIK}/yenile", json={"refresh_token": refresh}, headers={"X-Tenant": "alfa"}
    )
    assert r.status_code == 401

    # Başkasının oturumu görünmez (404): admin'in oturumu bu kullanıcıya kapalı.
    r = await kurulu_istemci.get(f"{KIMLIK}/oturumlar", headers=admin_h)
    admin_oturum = r.json()["data"][0]["id"]
    r = await kurulu_istemci.delete(f"{KIMLIK}/oturumlar/{admin_oturum}", headers=h)
    assert r.status_code == 404


async def test_parola_politikasi_uygulanir(
    test_db: str, kurulu_istemci: AsyncClient, temiz_guvenlik: AsyncEngine
) -> None:
    await _guvenlik_ayarla(
        temiz_guvenlik,
        "alfa",
        {"parola": {"min_uzunluk": 12, "buyuk_kucuk": True, "rakam": True}},
    )
    admin_h = await _giris(kurulu_istemci, ALFA)

    # Yeni kullanıcı: zayıf parola 422, güçlü parola 201.
    r = await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "s23-zayif@alfa.test", "parola": "zayifpar1", "ad_soyad": "Z"},
        headers=admin_h,
    )
    assert r.status_code == 422, r.text
    r = await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "s23-guclu@alfa.test", "parola": "GucluParola123", "ad_soyad": "G"},
        headers=admin_h,
    )
    assert r.status_code == 201, r.text

    # Parola değiştirme de politikaya tabidir.
    h = await _giris(
        kurulu_istemci,
        {"slug": "alfa", "eposta": "s23-guclu@alfa.test", "parola": "GucluParola123"},
    )
    r = await kurulu_istemci.post(
        f"{KIMLIK}/parola-degistir",
        json={"eski_parola": "GucluParola123", "yeni_parola": "kisa1234"},
        headers=h,
    )
    assert r.status_code == 422


async def test_tenant_2fa_zorunlulugu_kurulum_akisi(
    test_db: str, kurulu_istemci: AsyncClient, temiz_guvenlik: AsyncEngine
) -> None:
    admin_h = await _giris(kurulu_istemci, ALFA)
    eposta = await _kullanici_ac(kurulu_istemci, admin_h)
    await _guvenlik_ayarla(temiz_guvenlik, "alfa", {"iki_asama_zorunlu": True})

    # 2FA'sız kullanıcı tam token alamaz — kurulum-gerekli geçici token döner.
    r = await kurulu_istemci.post(
        f"{KIMLIK}/token",
        data={"username": eposta, "password": "Deneme12345!"},
        headers={"X-Tenant": "alfa"},
    )
    veri = r.json()["data"]
    assert veri["iki_asama_kurulum_gerekli"] is True and veri["access_token"] == ""
    gecici = veri["gecici_token"]
    gh = {"X-Tenant": "alfa", "Authorization": f"Bearer {gecici}"}

    # Geçici tokenla kurulum uçları çalışır; başka uç çalışmaz.
    r = await kurulu_istemci.get(f"{KIMLIK}/ben", headers=gh)
    assert r.status_code == 401  # access değil
    r = await kurulu_istemci.post(f"{KIMLIK}/2fa-kur", headers=gh)
    assert r.status_code == 200, r.text
    sir = r.json()["data"]["sir"]
    r = await kurulu_istemci.post(
        f"{KIMLIK}/2fa-etkinlestir", json={"kod": kod_uret(sir)}, headers=gh
    )
    assert r.status_code == 200, r.text

    # Artık standart 2FA girişi çalışır.
    r = await kurulu_istemci.post(
        f"{KIMLIK}/token",
        data={"username": eposta, "password": "Deneme12345!"},
        headers={"X-Tenant": "alfa"},
    )
    veri = r.json()["data"]
    assert veri["iki_asama_gerekli"] is True
    r = await kurulu_istemci.post(
        f"{KIMLIK}/2fa-dogrula",
        json={"gecici_token": veri["gecici_token"], "kod": kod_uret(sir)},
        headers={"X-Tenant": "alfa"},
    )
    assert r.status_code == 200 and r.json()["data"]["access_token"]


async def test_ip_izin_listesi_erisimi_kisitlar(
    test_db: str, kurulu_istemci: AsyncClient, temiz_guvenlik: AsyncEngine
) -> None:
    admin_h = await _giris(kurulu_istemci, ALFA)

    # httpx ASGI istemcisinin IP'si 127.0.0.1'dir: liste eşleşirse erişim sürer.
    await _guvenlik_ayarla(temiz_guvenlik, "alfa", {"ip_izin_listesi": ["127.0.0.1/32"]})
    r = await kurulu_istemci.get("/api/v1/kimlik/ben", headers=admin_h)
    assert r.status_code == 200, r.text

    # Eşleşmeyen ağ: tüm tenant istekleri 403 IP_KISITLI.
    await _guvenlik_ayarla(temiz_guvenlik, "alfa", {"ip_izin_listesi": ["203.0.113.0/24"]})
    r = await kurulu_istemci.get("/api/v1/kimlik/ben", headers=admin_h)
    assert r.status_code == 403
    assert r.json()["hata_kodu"] == "IP_KISITLI"
