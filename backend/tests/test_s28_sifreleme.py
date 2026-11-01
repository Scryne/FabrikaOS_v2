"""S28 (ADR-0047): TOTP sırrının veritabanında şifreli durması — tip, anahtar döndürme, göç."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Iterator
from types import SimpleNamespace

import asyncpg
import pytest
from cryptography.fernet import Fernet
from httpx import AsyncClient

from app.core.db import fanout
from app.core.security import sifreleme
from app.core.security.totp import kod_uret
from tests.conftest import ALFA, TEST_URL

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_S26B = "d4f6b8a0c2e3"


@pytest.fixture
def anahtarlar(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """``get_settings``'i değiştirip anahtar önbelleğini sıfırlar; testten sonra geri yükler."""

    def ayarla(liste: str, secret: str = "test-secret-" + "x" * 32) -> None:
        monkeypatch.setattr(
            sifreleme,
            "get_settings",
            lambda: SimpleNamespace(veri_sifreleme_anahtarlari=liste, secret_key=secret),
        )
        sifreleme.anahtar_onbellegini_temizle()

    yield ayarla
    monkeypatch.undo()
    sifreleme.anahtar_onbellegini_temizle()


def test_sifrele_coz_ve_eski_duz_metin() -> None:
    sir = "JBSWY3DPEHPK3PXP"
    s = sifreleme.sifrele(sir)
    assert s.startswith("f1:") and sir not in s
    assert sifreleme.sifrele(sir) != s  # rastgele IV: aynı sır iki kez aynı görünmez
    assert sifreleme.coz(s) == sir
    assert sifreleme.coz(sir) == sir  # göç öncesi düz metin olduğu gibi okunur


def test_anahtar_dondurme_eski_kaydi_kirmaz(anahtarlar: object) -> None:
    eski, yeni = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    anahtarlar(eski)  # type: ignore[operator]
    kayit = sifreleme.sifrele("SIR")
    anahtarlar(f"{yeni},{eski}")  # type: ignore[operator]  # yeni birincil, eski okunur
    assert sifreleme.coz(kayit) == "SIR"
    donmus = sifreleme.yeniden_sifrele(kayit)
    anahtarlar(yeni)  # type: ignore[operator]  # eski anahtar emekli
    assert sifreleme.coz(donmus) == "SIR"
    with pytest.raises(RuntimeError, match="çözülemedi"):
        sifreleme.coz(kayit)


def test_turetilmis_anahtar_ayri_anahtara_geciste_okunur(anahtarlar: object) -> None:
    anahtarlar("")  # type: ignore[operator]  # yalnız SECRET_KEY'den türetilmiş
    kayit = sifreleme.sifrele("SIR")
    anahtarlar(Fernet.generate_key().decode())  # type: ignore[operator]
    assert sifreleme.coz(kayit) == "SIR"  # türetilmiş anahtar son okuma anahtarı olarak kalır


async def _ham_sir(eposta: str) -> str | None:
    conn = await asyncpg.connect(_DSN)
    try:
        return await conn.fetchval(
            "SELECT totp_sirri FROM tenant_alfa.kullanici WHERE eposta = $1", eposta
        )
    finally:
        await conn.close()


async def _giris(istemci: AsyncClient, eposta: str, parola: str) -> dict[str, str]:
    r = await istemci.post(
        "/api/v1/kimlik/token",
        data={"username": eposta, "password": parola},
        headers={"X-Tenant": ALFA["slug"]},
    )
    assert r.status_code == 200, r.text
    return {"X-Tenant": ALFA["slug"], "Authorization": f"Bearer {r.json()['data']['access_token']}"}


async def test_totp_sirri_veritabaninda_sifreli_goc_up_down(
    test_db: str, kurulu_istemci: AsyncClient
) -> None:
    admin = await _giris(kurulu_istemci, ALFA["eposta"], ALFA["parola"])
    eposta, parola = f"s28-{uuid.uuid4().hex[:8]}@alfa.test", "Deneme12345!"
    r = await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": eposta, "parola": parola, "ad_soyad": "S28", "roller": ["izleyici"]},
        headers=admin,
    )
    assert r.status_code == 201, r.text
    h = await _giris(kurulu_istemci, eposta, parola)

    r = await kurulu_istemci.post("/api/v1/kimlik/2fa-kur", headers=h)
    assert r.status_code == 200, r.text
    sir = r.json()["data"]["sir"]
    ham = await _ham_sir(eposta)
    assert ham is not None and ham.startswith("f1:") and sir not in ham

    # Çözme yolu: etkinleştirme kodu şifreli sırla doğrulanır.
    r = await kurulu_istemci.post(
        "/api/v1/kimlik/2fa-etkinlestir", json={"kod": kod_uret(sir)}, headers=h
    )
    assert r.status_code == 200, r.text

    # Göç geri alınınca düz metne döner, yeniden uygulanınca şifrelenir.
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _S26B, db_url=TEST_URL)
    assert await _ham_sir(eposta) == sir
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    ham2 = await _ham_sir(eposta)
    assert ham2 is not None and ham2.startswith("f1:") and sifreleme.coz(ham2) == sir


async def test_webhook_imza_anahtari_veritabaninda_sifreli(kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA["eposta"], ALFA["parola"])
    r = await kurulu_istemci.post(
        "/api/v1/webhooklar",
        json={"ad": f"S28-{uuid.uuid4().hex[:6]}", "url": "https://ornek.test/kanca"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    veri = r.json()["data"]
    conn = await asyncpg.connect(_DSN)
    try:
        ham = await conn.fetchval(
            "SELECT gizli_anahtar FROM tenant_alfa.webhook_abonelikleri WHERE id = $1", veri["id"]
        )
    finally:
        await conn.close()
    assert ham.startswith("f1:") and veri["gizli_anahtar"] not in ham
    assert sifreleme.coz(ham) == veri["gizli_anahtar"]  # imza için tam hâli geri gelir
