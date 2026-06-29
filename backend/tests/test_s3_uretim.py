"""S3 entegrasyon testleri: makine/üretim uçları, OEE, hypertable, RBAC, izolasyon."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import ALFA, BETA

KIMLIK = "/api/v1/kimlik"


async def _giris(istemci: AsyncClient, t: dict) -> str:
    r = await istemci.post(
        f"{KIMLIK}/token",
        data={"username": t["eposta"], "password": t["parola"]},
        headers={"X-Tenant": t["slug"]},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


def _baslik(slug: str, access: str) -> dict[str, str]:
    return {"X-Tenant": slug, "Authorization": f"Bearer {access}"}


async def test_makine_olustur_listele_detay(kurulu_istemci: AsyncClient) -> None:
    access = await _giris(kurulu_istemci, ALFA)
    h = _baslik("alfa", access)

    r = await kurulu_istemci.post(
        "/api/v1/makineler", json={"kod": "MAK-A1", "ad": "Pres Hattı"}, headers=h
    )
    assert r.status_code == 201, r.text
    makine_id = r.json()["data"]["id"]
    assert r.json()["data"]["durum"] == "durdu"

    r = await kurulu_istemci.get(f"/api/v1/makineler/{makine_id}", headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["kod"] == "MAK-A1"

    r = await kurulu_istemci.get("/api/v1/makineler", headers=h)
    assert r.status_code == 200
    assert "MAK-A1" in [m["kod"] for m in r.json()["data"]]


async def test_makine_durum_guncelle_ve_gecersiz(kurulu_istemci: AsyncClient) -> None:
    access = await _giris(kurulu_istemci, ALFA)
    h = _baslik("alfa", access)
    mid = (
        await kurulu_istemci.post(
            "/api/v1/makineler", json={"kod": "MAK-DURUM", "ad": "Test"}, headers=h
        )
    ).json()["data"]["id"]

    r = await kurulu_istemci.patch(
        f"/api/v1/makineler/{mid}/durum", json={"durum": "calisiyor"}, headers=h
    )
    assert r.status_code == 200
    assert r.json()["data"]["durum"] == "calisiyor"

    r = await kurulu_istemci.patch(
        f"/api/v1/makineler/{mid}/durum", json={"durum": "ucan-daire"}, headers=h
    )
    assert r.status_code == 422


async def test_uretim_girisi_hypertable_ve_oee(kurulu_istemci: AsyncClient) -> None:
    access = await _giris(kurulu_istemci, ALFA)
    h = _baslik("alfa", access)
    mid = (
        await kurulu_istemci.post(
            "/api/v1/makineler", json={"kod": "MAK-OEE", "ad": "OEE Makinesi"}, headers=h
        )
    ).json()["data"]["id"]

    # Hypertable'a yazma (uretim_verileri)
    r = await kurulu_istemci.post(
        "/api/v1/uretim-verileri",
        json={
            "makine_id": mid,
            "planlanan_sure_dk": 480,
            "durus_sure_dk": 48,
            "toplam_adet": 500,
            "saglam_adet": 490,
            "ideal_cevrim_sn": 50,
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["id"] > 0  # hypertable Identity PK döndü

    # Okuma
    r = await kurulu_istemci.get(f"/api/v1/uretim-verileri?makine_id={mid}", headers=h)
    assert r.status_code == 200
    assert r.json()["meta"]["toplam"] == 1

    # OEE doğruluğu
    r = await kurulu_istemci.get(f"/api/v1/makineler/{mid}/oee", headers=h)
    assert r.status_code == 200
    d = r.json()["data"]
    assert d["kullanilabilirlik"] == pytest.approx(0.9, rel=1e-3)
    assert d["kalite"] == pytest.approx(0.98, rel=1e-3)
    assert d["performans"] == pytest.approx(0.96451, rel=1e-3)
    assert d["oee"] == pytest.approx(0.9 * 0.96451 * 0.98, rel=1e-2)
    assert d["kayit_sayisi"] == 1


async def test_oee_ozet(kurulu_istemci: AsyncClient) -> None:
    access = await _giris(kurulu_istemci, ALFA)
    h = _baslik("alfa", access)
    mid = (
        await kurulu_istemci.post(
            "/api/v1/makineler", json={"kod": "MAK-OZET", "ad": "Özet"}, headers=h
        )
    ).json()["data"]["id"]
    await kurulu_istemci.post(
        "/api/v1/uretim-verileri",
        json={
            "makine_id": mid,
            "planlanan_sure_dk": 100,
            "durus_sure_dk": 10,
            "toplam_adet": 90,
            "saglam_adet": 90,
            "ideal_cevrim_sn": 60,
        },
        headers=h,
    )
    r = await kurulu_istemci.get("/api/v1/oee/ozet", headers=h)
    assert r.status_code == 200
    kodlar = [s["makine_kod"] for s in r.json()["data"]]
    assert "MAK-OZET" in kodlar


async def test_uretim_rbac_403(kurulu_istemci: AsyncClient) -> None:
    # Admin bir izleyici (salt-okunur) kullanıcı açar.
    admin = await _giris(kurulu_istemci, ALFA)
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izleyici-u@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=_baslik("alfa", admin),
    )
    izleyici = await _giris(
        kurulu_istemci,
        {"slug": "alfa", "eposta": "izleyici-u@alfa.test", "parola": "Izleyici123!"},
    )
    h = _baslik("alfa", izleyici)

    # uretim:oku var → listeleme serbest
    assert (await kurulu_istemci.get("/api/v1/makineler", headers=h)).status_code == 200
    # uretim:yaz yok → oluşturma 403
    r = await kurulu_istemci.post(
        "/api/v1/makineler", json={"kod": "MAK-X", "ad": "Olmaz"}, headers=h
    )
    assert r.status_code == 403


async def test_uretim_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    access_alfa = await _giris(kurulu_istemci, ALFA)
    await kurulu_istemci.post(
        "/api/v1/makineler",
        json={"kod": "MAK-IZOLE-ALFA", "ad": "Alfa Makine"},
        headers=_baslik("alfa", access_alfa),
    )
    # Beta'da bu makine görünmemeli.
    access_beta = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.get("/api/v1/makineler", headers=_baslik("beta", access_beta))
    assert r.status_code == 200
    assert "MAK-IZOLE-ALFA" not in [m["kod"] for m in r.json()["data"]]
