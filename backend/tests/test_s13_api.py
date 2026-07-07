"""S13 API entegrasyon testleri — /tahmin uçları: eğitim 202, çıkarım, RBAC, izolasyon."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.modules.ai import artefakt, service
from app.modules.dys.depolama import nesne_depo_ayarla
from tests import test_s13_egitim as egitim_yardimci
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


def _h(slug: str, access: str) -> dict[str, str]:
    return {"X-Tenant": slug, "Authorization": f"Bearer {access}"}


@pytest_asyncio.fixture
async def ai_istemci(
    kurulu_istemci: AsyncClient, test_engine: AsyncEngine
) -> AsyncIterator[AsyncClient]:
    sm = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    service.oturum_fabrikasi_ayarla(sm)
    service.es_zamanli_ayarla(True)  # POST /egit yanıt dönmeden eğitimi bitirir
    nesne_depo_ayarla(egitim_yardimci._DEPO)
    await egitim_yardimci._alfa_seed(sm)
    yield kurulu_istemci
    service.oturum_fabrikasi_ayarla(None)
    service.es_zamanli_ayarla(False)
    nesne_depo_ayarla(None)
    artefakt.onbellek_temizle()


async def _egit(istemci: AsyncClient, h: dict[str, str], tur: str) -> dict:
    r = await istemci.post("/api/v1/tahmin/egit", json={"tur": tur}, headers=h)
    assert r.status_code == 202, r.text
    return r.json()["data"]


async def test_egit_202_ve_model_hazir(ai_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(ai_istemci, ALFA))
    kayit = await _egit(ai_istemci, h, "oee")
    assert kayit["durum"] == "egitiliyor"  # 202 anlık görüntüsü
    assert kayit["surum"] >= 1

    r = await ai_istemci.get("/api/v1/tahmin/modeller?tur=oee", headers=h)
    assert r.status_code == 200, r.text
    modeller = r.json()["data"]
    guncel = next(m for m in modeller if m["id"] == kayit["id"])
    assert guncel["durum"] == "hazir"
    assert guncel["aktif"] is True
    assert guncel["metrikler"]["satir_sayisi"] > 0
    assert "nesne_anahtari" not in guncel  # depolama iç detayı sızmaz


async def test_dort_tahmin_ucu_calisir(ai_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(ai_istemci, ALFA))
    for tur, yol in (
        ("kestirimci_bakim", "kestirimci-bakim"),
        ("oee", "oee"),
        ("stok", "stok"),
        ("anomali", "anomali"),
    ):
        await _egit(ai_istemci, h, tur)
        r = await ai_istemci.get(f"/api/v1/tahmin/{yol}", headers=h)
        assert r.status_code == 200, (tur, r.text)
        veri = r.json()["data"]
        assert veri["tur"] == tur
        assert veri["model_surum"] >= 1
        assert isinstance(veri["sonuclar"], list)
    # kestirimci bakım sonucu alan sözleşmesi
    r = await ai_istemci.get("/api/v1/tahmin/kestirimci-bakim", headers=h)
    ilk = r.json()["data"]["sonuclar"][0]
    assert {"makine_id", "risk_skoru", "seviye"} <= set(ilk)


async def test_gecmis_listelenir(ai_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(ai_istemci, ALFA))
    await _egit(ai_istemci, h, "oee")
    await ai_istemci.get("/api/v1/tahmin/oee", headers=h)
    r = await ai_istemci.get("/api/v1/tahmin/gecmis?tur=oee", headers=h)
    assert r.status_code == 200, r.text
    govde = r.json()
    assert govde["meta"]["toplam"] >= 1
    assert govde["data"][0]["tur"] == "oee"
    assert govde["data"][0]["sonuc_sayisi"] >= 1


async def test_gecersiz_tur_422(ai_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(ai_istemci, ALFA))
    r = await ai_istemci.post("/api/v1/tahmin/egit", json={"tur": "bilinmeyen"}, headers=h)
    assert r.status_code == 422, r.text
    r = await ai_istemci.get("/api/v1/tahmin/modeller?tur=bilinmeyen", headers=h)
    assert r.status_code == 422, r.text


async def test_izleyici_okur_ama_egitemez(ai_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(ai_istemci, ALFA))
    await _egit(ai_istemci, admin, "oee")
    await ai_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izleyici@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izleyici = _h(
        "alfa",
        await _giris(
            ai_istemci,
            {"slug": "alfa", "eposta": "izleyici@alfa.test", "parola": "Izleyici123!"},
        ),
    )
    # ai:oku var → tahmin okur
    r = await ai_istemci.get("/api/v1/tahmin/oee", headers=izleyici)
    assert r.status_code == 200, r.text
    # ai:egit yok → eğitim 403 (görev ayrımı)
    r = await ai_istemci.post("/api/v1/tahmin/egit", json={"tur": "oee"}, headers=izleyici)
    assert r.status_code == 403, r.text


async def test_izolasyon_beta_alfanin_modelini_kullanamaz(ai_istemci: AsyncClient) -> None:
    alfa = _h("alfa", await _giris(ai_istemci, ALFA))
    await _egit(ai_istemci, alfa, "oee")
    beta = _h("beta", await _giris(ai_istemci, BETA))
    # alfa'da model hazır ama beta şemasında aktif model yok → 404
    r = await ai_istemci.get("/api/v1/tahmin/oee", headers=beta)
    assert r.status_code == 404, r.text
    # beta'nın model listesi alfa kayıtlarını içermez
    r = await ai_istemci.get("/api/v1/tahmin/modeller", headers=beta)
    assert all(m["durum"] != "hazir" for m in r.json()["data"])


async def test_kimliksiz_401(ai_istemci: AsyncClient) -> None:
    r = await ai_istemci.get("/api/v1/tahmin/oee", headers={"X-Tenant": "alfa"})
    assert r.status_code == 401, r.text
