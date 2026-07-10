"""S18 dış portal testleri — firma-kapsam izolasyonu, 403 sınırları, iç görünürlük.

Kabul (yol haritası): dış portal YALNIZCA `dis-panel` kapsamı — dış kullanıcı iç uçlara
giremez, iç kullanıcı (admin dahil, firmasız) dış yüzeye giremez, firma A kullanıcısı
firma B'nin talebini göremez (liste dışı + detay 404).
"""

from __future__ import annotations

import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import ALFA
from tests.test_s16_entitlement import _giris

DIS = "/api/v1/dis"

FIRMA_A = "Dış Portal A.Ş."
FIRMA_B = "Dış Portal B Ltd."
KUL_A = {"slug": "alfa", "eposta": "portal-a@musteri.test", "parola": "PortalA123!"}
KUL_B = {"slug": "alfa", "eposta": "portal-b@musteri.test", "parola": "PortalB123!"}
KUL_FIRMASIZ = {"slug": "alfa", "eposta": "portal-bos@musteri.test", "parola": "PortalBos123!"}


@pytest_asyncio.fixture
async def kurulum(kurulu_istemci: AsyncClient) -> dict[str, object]:
    """Firma A/B + dis-panel kullanıcıları (idempotent — 409'lar yok sayılır)."""
    admin = await _giris(kurulu_istemci, ALFA)

    firma_idler: dict[str, int] = {}
    r = await kurulu_istemci.get("/api/v1/firmalar", params={"adet": 100}, headers=admin)
    mevcut = {f["ad"]: f["id"] for f in r.json()["data"]}
    for ad in (FIRMA_A, FIRMA_B):
        if ad in mevcut:
            firma_idler[ad] = mevcut[ad]
        else:
            r = await kurulu_istemci.post("/api/v1/firmalar", json={"ad": ad}, headers=admin)
            assert r.status_code == 201, r.text
            firma_idler[ad] = r.json()["data"]["id"]

    for kul, firma_ad in ((KUL_A, FIRMA_A), (KUL_B, FIRMA_B)):
        await kurulu_istemci.post(
            "/api/v1/kullanicilar",
            json={
                "eposta": kul["eposta"],
                "parola": kul["parola"],
                "ad_soyad": f"{firma_ad} irtibat",
                "roller": ["dis-panel"],
                "firma_id": firma_idler[firma_ad],
            },
            headers=admin,
        )
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={
            "eposta": KUL_FIRMASIZ["eposta"],
            "parola": KUL_FIRMASIZ["parola"],
            "roller": ["dis-panel"],
        },
        headers=admin,
    )
    return {"admin": admin, "firma_idler": firma_idler}


async def test_dis_talep_olustur_ve_ic_listede_gorunur(
    kurulu_istemci: AsyncClient, kurulum: dict[str, object]
) -> None:
    a = await _giris(kurulu_istemci, KUL_A)
    r = await kurulu_istemci.post(
        f"{DIS}/talepler",
        json={"baslik": "Sevkiyat gecikmesi", "aciklama": "Sipariş #42 gecikti", "tur": "destek"},
        headers=a,
    )
    assert r.status_code == 201, r.text
    veri = r.json()["data"]
    assert veri["kod"].startswith("TL-")
    assert veri["durum"] == "acik"
    assert "firma_id" not in veri  # iç alanlar dış DTO'da sızmaz
    assert "atanan_kullanici_id" not in veri

    # İç ekip aynı talebi kendi listesinde görür (tek doğruluk kaynağı).
    admin = kurulum["admin"]
    r = await kurulu_istemci.get(
        "/api/v1/talepler", params={"arama": "Sevkiyat gecikmesi"}, headers=admin
    )
    kayitlar = [t for t in r.json()["data"] if t["baslik"] == "Sevkiyat gecikmesi"]
    assert kayitlar, r.text
    firma_idler = kurulum["firma_idler"]
    assert kayitlar[0]["firma_id"] == firma_idler[FIRMA_A]  # type: ignore[index]


async def test_firma_izolasyonu_liste_ve_detay(
    kurulu_istemci: AsyncClient, kurulum: dict[str, object]
) -> None:
    a = await _giris(kurulu_istemci, KUL_A)
    b = await _giris(kurulu_istemci, KUL_B)

    r = await kurulu_istemci.post(
        f"{DIS}/talepler", json={"baslik": "A firmasının gizli talebi"}, headers=a
    )
    talep_id = r.json()["data"]["id"]

    # B'nin listesinde A'nın talebi YOK.
    r = await kurulu_istemci.get(f"{DIS}/talepler", params={"adet": 100}, headers=b)
    assert r.status_code == 200
    assert all(t["id"] != talep_id for t in r.json()["data"])

    # B, A'nın talebine ID ile de erişemez → 404 (görünmez).
    r = await kurulu_istemci.get(f"{DIS}/talepler/{talep_id}", headers=b)
    assert r.status_code == 404

    # A kendi talebini görür.
    r = await kurulu_istemci.get(f"{DIS}/talepler/{talep_id}", headers=a)
    assert r.status_code == 200


async def test_firmasiz_dis_kullanici_403(
    kurulu_istemci: AsyncClient, kurulum: dict[str, object]
) -> None:
    bos = await _giris(kurulu_istemci, KUL_FIRMASIZ)
    for yol in (f"{DIS}/talepler", f"{DIS}/durum"):
        r = await kurulu_istemci.get(yol, headers=bos)
        assert r.status_code == 403, f"{yol}: {r.status_code}"


async def test_admin_firmasiz_dis_yuzeye_giremez(
    kurulu_istemci: AsyncClient, kurulum: dict[str, object]
) -> None:
    # Admin tüm izinlere (dis:erisim dahil) sahiptir ama firma bağlantısı yoktur → 403.
    admin = kurulum["admin"]
    r = await kurulu_istemci.get(f"{DIS}/talepler", headers=admin)  # type: ignore[arg-type]
    assert r.status_code == 403


async def test_dis_kullanici_ic_uclara_giremez(
    kurulu_istemci: AsyncClient, kurulum: dict[str, object]
) -> None:
    a = await _giris(kurulu_istemci, KUL_A)
    for metod, yol in (
        ("GET", "/api/v1/makineler"),
        ("GET", "/api/v1/talepler"),  # iç talep listesi bile yasak (talep:oku yok)
        ("GET", "/api/v1/kullanicilar"),
        ("GET", "/api/v1/malzemeler"),
        ("GET", "/api/v1/webhooklar"),
        ("POST", "/api/v1/talepler"),
    ):
        r = await kurulu_istemci.request(metod, yol, json={}, headers=a)
        assert r.status_code == 403, f"{metod} {yol}: {r.status_code} {r.text}"


async def test_dis_durum_ozeti(kurulu_istemci: AsyncClient, kurulum: dict[str, object]) -> None:
    a = await _giris(kurulu_istemci, KUL_A)
    await kurulu_istemci.post(f"{DIS}/talepler", json={"baslik": "Özet için talep"}, headers=a)

    r = await kurulu_istemci.get(f"{DIS}/durum", headers=a)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["firma_ad"] == FIRMA_A
    assert veri["toplam"] >= 1
    assert veri["acik"] >= 1
    assert len(veri["son_talepler"]) >= 1
    assert {d["durum"] for d in veri["durum_dagilimi"]} >= {"acik"}


async def test_gecersiz_tur_422(kurulu_istemci: AsyncClient, kurulum: dict[str, object]) -> None:
    a = await _giris(kurulu_istemci, KUL_A)
    r = await kurulu_istemci.post(
        f"{DIS}/talepler", json={"baslik": "X", "tur": "olmayan-tur"}, headers=a
    )
    assert r.status_code == 422
