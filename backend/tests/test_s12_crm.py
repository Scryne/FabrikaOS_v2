"""S12 entegrasyon: CRM firma + ortak — CRUD, doğrulama, RBAC, tenant izolasyonu."""

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


async def _firma(istemci: AsyncClient, h: dict[str, str], ad: str, **ek: object) -> dict:
    r = await istemci.post("/api/v1/firmalar", json={"ad": ad, "tip": "musteri", **ek}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_firma_olustur_listele(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    f = await _firma(kurulu_istemci, h, "Acme A.Ş.", sektor="Otomotiv", il="Bursa")
    assert f["tip"] == "musteri"
    r = await kurulu_istemci.get("/api/v1/firmalar?arama=Acme", headers=h)
    assert r.status_code == 200
    veri = r.json()
    assert veri["meta"]["toplam"] >= 1
    assert any(x["ad"] == "Acme A.Ş." for x in veri["data"])


async def test_firma_gecersiz_tip_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post("/api/v1/firmalar", json={"ad": "X", "tip": "kozmik"}, headers=h)
    assert r.status_code == 422, r.text


async def test_firma_guncelle(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    f = await _firma(kurulu_istemci, h, "Beta Tedarik", tip="tedarikci")
    r = await kurulu_istemci.patch(
        f"/api/v1/firmalar/{f['id']}", json={"il": "Ankara", "aktif": False}, headers=h
    )
    assert r.status_code == 200, r.text
    d = r.json()["data"]
    assert d["il"] == "Ankara"
    assert d["aktif"] is False


async def test_ortak_firma_bagi(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    f = await _firma(kurulu_istemci, h, "Kontaklı Firma")
    r = await kurulu_istemci.post(
        "/api/v1/ortaklar",
        json={"firma_id": f["id"], "ad_soyad": "Ayşe Yılmaz", "birincil": True},
        headers=h,
    )
    assert r.status_code == 201, r.text
    liste = await kurulu_istemci.get(f"/api/v1/ortaklar?firma_id={f['id']}", headers=h)
    assert liste.json()["meta"]["toplam"] == 1


async def test_ortak_firma_yok_404(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/ortaklar", json={"firma_id": 999999, "ad_soyad": "Yok"}, headers=h
    )
    assert r.status_code == 404, r.text


async def test_firma_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    # izleyici rolü: yalnız *:oku (crm:yaz yok)
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izle@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izle = _h(
        "alfa",
        await _giris(
            kurulu_istemci,
            {"slug": "alfa", "eposta": "izle@alfa.test", "parola": "Izleyici123!"},
        ),
    )
    r = await kurulu_istemci.post("/api/v1/firmalar", json={"ad": "Yetkisiz"}, headers=izle)
    assert r.status_code == 403, r.text
    # okuma serbest
    ok = await kurulu_istemci.get("/api/v1/firmalar", headers=izle)
    assert ok.status_code == 200


async def test_firma_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    fa = await _firma(kurulu_istemci, ha, "İzole Firma")
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    r = await kurulu_istemci.get(f"/api/v1/firmalar/{fa['id']}", headers=hb)
    assert r.status_code == 404, r.text
