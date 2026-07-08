"""S15 seed + kiosk salt-okunurluğu: `kiosk` rolü yalnız uretim:oku taşır.

Salt-okunurluk UI vaadi değil API garantisidir: kiosk rolüyle ikiz durumunu okumak
200, herhangi bir yazma ucu 403 döner (kabul kriteri).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.kimlik.izinler import VARSAYILAN_ROLLER
from tests.conftest import ALFA


def test_kiosk_rolu_salt_okunur() -> None:
    assert VARSAYILAN_ROLLER["kiosk"] == frozenset({"uretim:oku"})
    assert not any(izin.endswith((":yaz", ":sil", ":onay")) for izin in VARSAYILAN_ROLLER["kiosk"])


async def _giris(istemci: AsyncClient, slug: str, eposta: str, parola: str) -> dict[str, str]:
    r = await istemci.post(
        "/api/v1/kimlik/token",
        data={"username": eposta, "password": parola},
        headers={"X-Tenant": slug},
    )
    assert r.status_code == 200, r.text
    return {"X-Tenant": slug, "Authorization": f"Bearer {r.json()['data']['access_token']}"}


@pytest_asyncio.fixture
async def kiosk_basligi(kurulu_istemci: AsyncClient) -> AsyncIterator[dict[str, str]]:
    admin = await _giris(kurulu_istemci, "alfa", ALFA["eposta"], ALFA["parola"])
    r = await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "kiosk@alfa.test", "parola": "Kiosk1234!", "roller": ["kiosk"]},
        headers=admin,
    )
    assert r.status_code in (200, 201, 409), r.text  # idempotent (tekrar koşuda 409)
    yield await _giris(kurulu_istemci, "alfa", "kiosk@alfa.test", "Kiosk1234!")


@pytest.mark.asyncio
async def test_kiosk_ikiz_durumunu_okur(
    kurulu_istemci: AsyncClient, kiosk_basligi: dict[str, str]
) -> None:
    for yol in ("/api/v1/ikiz/durum", "/api/v1/ikiz/yerlesim", "/api/v1/makineler"):
        r = await kurulu_istemci.get(yol, headers=kiosk_basligi)
        assert r.status_code == 200, f"{yol}: {r.text}"


@pytest.mark.asyncio
async def test_kiosk_yazma_uclari_403(
    kurulu_istemci: AsyncClient, kiosk_basligi: dict[str, str]
) -> None:
    # Kendi modülü dahil temsili yazma uçları — tümü 403 (gövde doğrulamasından önce).
    denemeler = [
        ("PUT", "/api/v1/ikiz/yerlesim", {"dugumler": []}),
        ("POST", "/api/v1/makineler", {"kod": "KX", "ad": "X"}),
        ("POST", "/api/v1/uretim-verileri", {"makine_id": 1}),
        ("POST", "/api/v1/is-emirleri", {"baslik": "X"}),
        ("POST", "/api/v1/malzemeler", {"kod": "KX", "ad": "X", "birim": "adet"}),
        ("POST", "/api/v1/raporlar", {"tur": "uretim", "bicim": "pdf"}),
    ]
    for metod, yol, govde in denemeler:
        r = await kurulu_istemci.request(metod, yol, json=govde, headers=kiosk_basligi)
        assert r.status_code == 403, f"{metod} {yol}: {r.status_code} {r.text}"
