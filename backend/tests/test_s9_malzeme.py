"""S9 entegrasyon: malzeme CRUD + kritik liste + RBAC + tenant izolasyonu."""

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


async def _malzeme(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"kod": "MLZ-1", "ad": "Rulman 6203", "birim": "adet", **ek}
    r = await istemci.post("/api/v1/malzemeler", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_malzeme_olustur_varsayilanlar(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _malzeme(kurulu_istemci, h, kod="MLZ-VAR")
    assert d["mevcut_miktar"] == 0
    assert d["aktif"] is True
    assert d["kritik"] is False


async def test_malzeme_gecersiz_birim_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/malzemeler",
        json={"kod": "MLZ-X", "ad": "X", "birim": "sihirli"},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_malzeme_kod_cakismasi_409(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await _malzeme(kurulu_istemci, h, kod="MLZ-DUP")
    r = await kurulu_istemci.post(
        "/api/v1/malzemeler", json={"kod": "MLZ-DUP", "ad": "Y", "birim": "adet"}, headers=h
    )
    assert r.status_code == 409, r.text


async def test_malzeme_guncelle_esikler(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _malzeme(kurulu_istemci, h, kod="MLZ-UPD")
    r = await kurulu_istemci.patch(
        f"/api/v1/malzemeler/{d['id']}",
        json={"kritik_stok": 5, "ad": "Rulman (güncel)"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["kritik_stok"] == 5
    assert r.json()["data"]["ad"] == "Rulman (güncel)"


async def test_kritik_liste(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    # mevcut 0, kritik 5 → kritik listede; kritik 0 olan listelenmez.
    await _malzeme(kurulu_istemci, h, kod="MLZ-KRT", kritik_stok=5)
    await _malzeme(kurulu_istemci, h, kod="MLZ-NORMAL", kritik_stok=0)
    r = await kurulu_istemci.get("/api/v1/stok/kritik", headers=h)
    assert r.status_code == 200, r.text
    kodlar = [m["kod"] for m in r.json()["data"]]
    assert "MLZ-KRT" in kodlar
    assert "MLZ-NORMAL" not in kodlar


async def test_malzeme_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izl-st@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izl = _h(
        "alfa",
        await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "izl-st@alfa.test", "parola": "Izleyici123!"}
        ),
    )
    # stok:oku var → liste 200
    assert (await kurulu_istemci.get("/api/v1/malzemeler", headers=izl)).status_code == 200
    # stok:yaz yok → oluştur 403
    r = await kurulu_istemci.post(
        "/api/v1/malzemeler", json={"kod": "MLZ-RBAC", "ad": "X", "birim": "adet"}, headers=izl
    )
    assert r.status_code == 403, r.text


async def test_malzeme_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    da = await _malzeme(kurulu_istemci, ha, kod="MLZ-GIZLI-A")
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    # beta listede görmez + id ile 404
    r = await kurulu_istemci.get("/api/v1/malzemeler", headers=hb)
    assert "MLZ-GIZLI-A" not in [m["kod"] for m in r.json()["data"]]
    assert (
        await kurulu_istemci.get(f"/api/v1/malzemeler/{da['id']}", headers=hb)
    ).status_code == 404
