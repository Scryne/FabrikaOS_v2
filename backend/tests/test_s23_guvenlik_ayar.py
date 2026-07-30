"""S23 tenant güvenlik ayarları — sır maskeleme (saf) + platform ucu davranışı.

OIDC istemci sırrı yapılandırmanın en hassas parçasıdır: platform panelinde
görüntülenmemeli, düzenlemede kaybolmamalı ve denetim izine düz metin yazılmamalı.
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.platform.guvenlik_ayar import MASKE, ayarlari_maskele, sirri_koru
from tests.test_s17_platform_kimlik import (  # noqa: F401 (fixture zinciri: platform_db → oturum)
    oturum,
    platform_db,
    platform_giris,
)

PLATFORM = "/api/v1/platform"


def _oidc(sir: str = "cok-gizli-sir") -> dict[str, Any]:
    return {
        "oidc": {
            "aktif": True,
            "issuer": "https://idp.test",
            "istemci_id": "fos",
            "istemci_sirri": sir,
            "donus_url": "https://app.test/sso/donus",
        },
        "iki_asama_zorunlu": True,
    }


# --- Saf birim ---
def test_maskele_sirri_gizler_diger_alanlari_korur() -> None:
    maskeli = ayarlari_maskele(_oidc())
    assert maskeli is not None
    assert maskeli["oidc"]["istemci_sirri"] == MASKE
    assert maskeli["oidc"]["issuer"] == "https://idp.test"
    assert maskeli["iki_asama_zorunlu"] is True


def test_maskele_kaynagi_degistirmez() -> None:
    kaynak = _oidc()
    ayarlari_maskele(kaynak)
    assert kaynak["oidc"]["istemci_sirri"] == "cok-gizli-sir"  # derin kopya


def test_maskele_oidc_yoksa_ve_none_ise_guvenli() -> None:
    assert ayarlari_maskele(None) is None
    assert ayarlari_maskele({"parola": {"min_uzunluk": 12}}) == {"parola": {"min_uzunluk": 12}}


def test_sirri_koru_maskeli_gelirse_mevcudu_tasir() -> None:
    korunmus = sirri_koru(_oidc(MASKE), _oidc("gercek-sir"))
    assert korunmus is not None
    assert korunmus["oidc"]["istemci_sirri"] == "gercek-sir"


def test_sirri_koru_bos_gelirse_mevcudu_tasir() -> None:
    korunmus = sirri_koru(_oidc(""), _oidc("gercek-sir"))
    assert korunmus is not None
    assert korunmus["oidc"]["istemci_sirri"] == "gercek-sir"


def test_sirri_koru_yeni_sir_verilmisse_onu_kullanir() -> None:
    korunmus = sirri_koru(_oidc("yeni-sir"), _oidc("eski-sir"))
    assert korunmus is not None
    assert korunmus["oidc"]["istemci_sirri"] == "yeni-sir"


def test_sirri_koru_none_ayarlari_sifirlar() -> None:
    # Varsayılana dönüş: SSO dahil her şey kapanır, sır taşınmaz.
    assert sirri_koru(None, _oidc("gercek-sir")) is None


# --- Platform ucu (entegrasyon) ---
@pytest.mark.asyncio
async def test_platform_guvenlik_ayari_yazilir_ve_sir_maskeli_doner(
    platform_db: None,  # noqa: F811 (pytest fixture enjeksiyonu — gölgeleme kasıtlı)
    kurulu_istemci: AsyncClient,
    test_engine: AsyncEngine,
) -> None:
    h = await platform_giris(kurulu_istemci)

    tenantlar = await kurulu_istemci.get(f"{PLATFORM}/tenantlar", headers=h)
    alfa = next(t for t in tenantlar.json()["data"] if t["slug"] == "alfa")

    yaz = await kurulu_istemci.put(
        f"{PLATFORM}/tenantlar/{alfa['id']}/guvenlik-ayarlari",
        json={"ayarlar": _oidc("ilk-sir")},
        headers=h,
    )
    assert yaz.status_code == 200, yaz.text
    # Yanıt maskeli: panel sırrı asla görmez.
    assert yaz.json()["data"]["oidc"]["istemci_sirri"] == MASKE

    # Detayda da maskeli döner.
    detay = await kurulu_istemci.get(f"{PLATFORM}/tenantlar/{alfa['id']}", headers=h)
    assert detay.json()["data"]["guvenlik_ayarlari"]["oidc"]["istemci_sirri"] == MASKE

    # DB'de gerçek sır durur (SSO çalışabilsin).
    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    async with sm() as db:
        ham = await db.scalar(
            text("SELECT guvenlik_ayarlari FROM public.tenant WHERE slug = 'alfa'")
        )
    assert ham["oidc"]["istemci_sirri"] == "ilk-sir"

    # Maskeli gövdeyle güncelleme sırrı SİLMEZ (panel düzenleme akışı).
    tekrar = await kurulu_istemci.put(
        f"{PLATFORM}/tenantlar/{alfa['id']}/guvenlik-ayarlari",
        json={"ayarlar": {**_oidc(MASKE), "iki_asama_zorunlu": False}},
        headers=h,
    )
    assert tekrar.status_code == 200
    async with sm() as db:
        ham2 = await db.scalar(
            text("SELECT guvenlik_ayarlari FROM public.tenant WHERE slug = 'alfa'")
        )
    assert ham2["oidc"]["istemci_sirri"] == "ilk-sir"
    assert ham2["iki_asama_zorunlu"] is False

    # Denetim izine düz metin sır yazılmaz.
    async with sm() as db:
        detaylar = (
            (
                await db.execute(
                    text(
                        "SELECT detay::text FROM public.platform_denetim_izi "
                        "WHERE eylem = 'guvenlik_ayarla'"
                    )
                )
            )
            .scalars()
            .all()
        )
    assert detaylar
    assert all("ilk-sir" not in d for d in detaylar)

    # Temizlik: ayarları sıfırla (diğer testler etkilenmesin).
    await kurulu_istemci.put(
        f"{PLATFORM}/tenantlar/{alfa['id']}/guvenlik-ayarlari",
        json={"ayarlar": None},
        headers=h,
    )
