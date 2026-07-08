"""S14 API entegrasyon testleri — /raporlar uçları: 202→hazir→indir, RBAC, izolasyon."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.modules.dys.depolama import nesne_depo_ayarla
from app.modules.rapor import service
from tests import test_s14_rapor_servis as servis_yardimci
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
async def rapor_istemci(
    kurulu_istemci: AsyncClient, test_engine: AsyncEngine
) -> AsyncIterator[AsyncClient]:
    sm = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    service.oturum_fabrikasi_ayarla(sm)
    service.es_zamanli_ayarla(True)  # POST /raporlar yanıt dönmeden üretimi bitirir
    nesne_depo_ayarla(servis_yardimci._DEPO)
    await servis_yardimci._alfa_seed(sm)
    yield kurulu_istemci
    service.oturum_fabrikasi_ayarla(None)
    service.es_zamanli_ayarla(False)
    nesne_depo_ayarla(None)


async def _olustur(istemci: AsyncClient, h: dict[str, str], govde: dict) -> dict:
    r = await istemci.post("/api/v1/raporlar", json=govde, headers=h)
    assert r.status_code == 202, r.text
    return r.json()["data"]


async def test_rapor_202_ve_hazir_ve_indir(rapor_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(rapor_istemci, ALFA))
    kayit = await _olustur(rapor_istemci, h, {"tur": "uretim", "bicim": "pdf", "gun": 30})
    assert kayit["durum"] == "kuyrukta"  # 202 anlık görüntüsü
    assert kayit["kod"].startswith("RP-")
    assert "nesne_anahtari" not in kayit  # depolama iç detayı sızmaz

    r = await rapor_istemci.get(f"/api/v1/raporlar/{kayit['id']}", headers=h)
    assert r.status_code == 200, r.text
    detay = r.json()["data"]
    assert detay["durum"] == "hazir"
    assert detay["boyut"] > 0
    assert detay["dosya_adi"] == f"{kayit['kod']}.pdf"

    r = await rapor_istemci.get(f"/api/v1/raporlar/{kayit['id']}/indir", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/pdf")
    assert kayit["kod"] in r.headers["content-disposition"]
    assert r.content.startswith(b"%PDF")
    assert len(r.content) == detay["boyut"]  # depodaki baytlarla birebir

    depodaki = servis_yardimci._DEPO.indir(f"tenant_alfa/rapor/{kayit['id']}/{kayit['kod']}.pdf")
    assert r.content == depodaki  # indirilen == MinIO'daki


async def test_rapor_listesi_ve_filtre(rapor_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(rapor_istemci, ALFA))
    await _olustur(rapor_istemci, h, {"tur": "stok", "bicim": "xlsx"})
    r = await rapor_istemci.get("/api/v1/raporlar?tur=stok&durum=hazir", headers=h)
    assert r.status_code == 200, r.text
    govde = r.json()
    assert govde["meta"]["toplam"] >= 1
    assert all(k["tur"] == "stok" and k["durum"] == "hazir" for k in govde["data"])


async def test_hazir_olmayan_rapor_indirilemez_409(
    rapor_istemci: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    h = _h("alfa", await _giris(rapor_istemci, ALFA))

    async def _bos(rapor_id: int, slug: str) -> None:
        return None  # planlamayı no-op yap → kayıt kuyrukta kalır

    monkeypatch.setattr(service, "uretim_planla", _bos)
    kayit = await _olustur(rapor_istemci, h, {"tur": "uretim", "bicim": "pdf"})
    r = await rapor_istemci.get(f"/api/v1/raporlar/{kayit['id']}/indir", headers=h)
    assert r.status_code == 409, r.text


async def test_gecersiz_tur_ve_bicim_422(rapor_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(rapor_istemci, ALFA))
    r = await rapor_istemci.post("/api/v1/raporlar", json={"tur": "bilinmeyen"}, headers=h)
    assert r.status_code == 422, r.text
    r = await rapor_istemci.post(
        "/api/v1/raporlar", json={"tur": "uretim", "bicim": "docx"}, headers=h
    )
    assert r.status_code == 422, r.text
    r = await rapor_istemci.get("/api/v1/raporlar?durum=bilinmeyen", headers=h)
    assert r.status_code == 422, r.text


async def test_izleyici_okur_ama_olusturamaz(rapor_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(rapor_istemci, ALFA))
    await _olustur(rapor_istemci, admin, {"tur": "uretim", "bicim": "pdf"})
    await rapor_istemci.post(
        "/api/v1/kullanicilar",
        json={
            "eposta": "rapor-izleyici@alfa.test",
            "parola": "Izleyici123!",
            "roller": ["izleyici"],
        },
        headers=admin,
    )
    izleyici = _h(
        "alfa",
        await _giris(
            rapor_istemci,
            {"slug": "alfa", "eposta": "rapor-izleyici@alfa.test", "parola": "Izleyici123!"},
        ),
    )
    # rapor:oku var → listeler
    r = await rapor_istemci.get("/api/v1/raporlar", headers=izleyici)
    assert r.status_code == 200, r.text
    # rapor:yaz yok → oluşturma 403 (görev ayrımı)
    r = await rapor_istemci.post(
        "/api/v1/raporlar", json={"tur": "uretim", "bicim": "pdf"}, headers=izleyici
    )
    assert r.status_code == 403, r.text
    # analitik:oku var → KPI okur
    r = await rapor_istemci.get("/api/v1/analitik/kpi", headers=izleyici)
    assert r.status_code == 200, r.text


async def test_izolasyon_beta_alfanin_raporunu_goremez(rapor_istemci: AsyncClient) -> None:
    alfa = _h("alfa", await _giris(rapor_istemci, ALFA))
    kayit = await _olustur(rapor_istemci, alfa, {"tur": "uretim", "bicim": "pdf"})
    beta = _h("beta", await _giris(rapor_istemci, BETA))
    r = await rapor_istemci.get(f"/api/v1/raporlar/{kayit['id']}", headers=beta)
    assert r.status_code == 404, r.text
    r = await rapor_istemci.get(f"/api/v1/raporlar/{kayit['id']}/indir", headers=beta)
    assert r.status_code == 404, r.text
    r = await rapor_istemci.get("/api/v1/raporlar", headers=beta)
    assert all(k["id"] != kayit["id"] for k in r.json()["data"])


async def test_kimliksiz_401(rapor_istemci: AsyncClient) -> None:
    r = await rapor_istemci.get("/api/v1/raporlar", headers={"X-Tenant": "alfa"})
    assert r.status_code == 401, r.text
