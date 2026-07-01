"""S10 entegrasyon: enerji ölçüm yaz/listele + CAGG trend + RBAC + izolasyon."""

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


async def _olcum(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"enerji_turu": "elektrik", "tuketim": 10, "birim": "kWh", **ek}
    r = await istemci.post("/api/v1/enerji-tuketimleri", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_olcum_yaz_listele(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    # Belirli zaman → trend testinin sorgu penceresinin dışında (test izolasyonu).
    await _olcum(kurulu_istemci, h, tuketim=12.5, zaman="2026-06-15T10:00:00Z")
    r = await kurulu_istemci.get("/api/v1/enerji-tuketimleri?enerji_turu=elektrik", headers=h)
    assert r.status_code == 200, r.text
    assert any(x["tuketim"] == 12.5 for x in r.json()["data"])


async def test_olcum_gecersiz_tur_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/enerji-tuketimleri",
        json={"enerji_turu": "plazma", "tuketim": 5, "birim": "kWh"},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_olcum_negatif_tuketim_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/enerji-tuketimleri",
        json={"enerji_turu": "elektrik", "tuketim": -3, "birim": "kWh"},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_trend_saatlik_toplar(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    # Aynı saat kovasında iki ölçüm → trend tek noktada toplam 30 (real-time aggregation).
    await _olcum(kurulu_istemci, h, tuketim=10, zaman="2026-07-01T08:05:00Z")
    await _olcum(kurulu_istemci, h, tuketim=20, zaman="2026-07-01T08:40:00Z")
    r = await kurulu_istemci.get(
        "/api/v1/enerji-tuketimleri/trend?enerji_turu=elektrik&aralik=saat"
        "&baslangic=2026-07-01T00:00:00Z&bitis=2026-07-02T00:00:00Z",
        headers=h,
    )
    assert r.status_code == 200, r.text
    noktalar = r.json()["data"]
    toplam = sum(n["toplam"] for n in noktalar)
    assert toplam == 30.0
    # Bir saatlik kova → tek nokta.
    assert len(noktalar) == 1


async def test_trend_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izl-en@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izl = _h(
        "alfa",
        await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "izl-en@alfa.test", "parola": "Izleyici123!"}
        ),
    )
    # enerji:oku var → trend 200
    assert (
        await kurulu_istemci.get("/api/v1/enerji-tuketimleri/trend", headers=izl)
    ).status_code == 200
    # enerji:yaz yok → yaz 403
    r = await kurulu_istemci.post(
        "/api/v1/enerji-tuketimleri",
        json={"enerji_turu": "elektrik", "tuketim": 1, "birim": "kWh"},
        headers=izl,
    )
    assert r.status_code == 403, r.text


async def test_enerji_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await _olcum(kurulu_istemci, ha, tuketim=99, zaman="2026-07-01T08:05:00Z")
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    r = await kurulu_istemci.get(
        "/api/v1/enerji-tuketimleri/trend?aralik=saat"
        "&baslangic=2026-07-01T00:00:00Z&bitis=2026-07-02T00:00:00Z",
        headers=hb,
    )
    assert r.status_code == 200, r.text
    assert sum(n["toplam"] for n in r.json()["data"]) == 0.0
