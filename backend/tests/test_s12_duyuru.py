"""S12 entegrasyon: duyuru — oto kod, yayınla/kaldır, önem, RBAC, tenant izolasyonu."""

from __future__ import annotations

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


def _h(slug: str, access: str) -> dict[str, str]:
    return {"X-Tenant": slug, "Authorization": f"Bearer {access}"}


async def _duyuru(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"baslik": "Bakım duyurusu", "icerik": "Cumartesi bakım var", "onem": "uyari", **ek}
    r = await istemci.post("/api/v1/duyurular", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_duyuru_oto_kod_taslak(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _duyuru(kurulu_istemci, h)
    assert d["kod"].startswith("DUY-")
    assert d["yayinda"] is False
    assert d["onem"] == "uyari"


async def test_duyuru_gecersiz_onem_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/duyurular", json={"baslik": "X", "onem": "felaket"}, headers=h
    )
    assert r.status_code == 422, r.text


async def test_duyuru_yayinla_kaldir(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _duyuru(kurulu_istemci, h)
    y = await kurulu_istemci.post(f"/api/v1/duyurular/{d['id']}/yayinla", headers=h)
    assert y.status_code == 200, y.text
    assert y.json()["data"]["yayinda"] is True
    # yayinda filtresi
    liste = await kurulu_istemci.get("/api/v1/duyurular?yayinda=true", headers=h)
    assert any(x["id"] == d["id"] for x in liste.json()["data"])
    # kaldır
    k = await kurulu_istemci.post(f"/api/v1/duyurular/{d['id']}/kaldir", headers=h)
    assert k.json()["data"]["yayinda"] is False


async def test_duyuru_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    # crm rolü duyuru:yaz içermez (görev ayrımı) ama duyuru:oku yok da → okuma da 403
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "crmci@alfa.test", "parola": "Crmci123!", "roller": ["crm"]},
        headers=admin,
    )
    crmci = _h(
        "alfa",
        await _giris(
            kurulu_istemci,
            {"slug": "alfa", "eposta": "crmci@alfa.test", "parola": "Crmci123!"},
        ),
    )
    r = await kurulu_istemci.post("/api/v1/duyurular", json={"baslik": "Yetkisiz"}, headers=crmci)
    assert r.status_code == 403, r.text


async def test_duyuru_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    da = await _duyuru(kurulu_istemci, ha)
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    r = await kurulu_istemci.get(f"/api/v1/duyurular/{da['id']}", headers=hb)
    assert r.status_code == 404, r.text
