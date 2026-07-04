"""S11 entegrasyon: İSG iş kazası + risk değerlendirme (matris) + RBAC + tenant izolasyonu."""

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


async def _kaza(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"tur": "kaza", "yer": "Montaj Hattı", "agirlik": "orta", **ek}
    r = await istemci.post("/api/v1/is-kazalari", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def _risk(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"baslik": "Yüksekte çalışma", "olasilik": 4, "siddet": 4, **ek}
    r = await istemci.post("/api/v1/risk-degerlendirmeleri", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_kaza_olustur_oto_kod(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _kaza(kurulu_istemci, h)
    assert d["kod"].startswith("KZ-")
    assert d["tur"] == "kaza"
    assert d["agirlik"] == "orta"


async def test_kaza_gecersiz_tur_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/is-kazalari", json={"tur": "belirsiz", "agirlik": "orta"}, headers=h
    )
    assert r.status_code == 422, r.text


async def test_kaza_gecersiz_agirlik_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/is-kazalari", json={"tur": "kaza", "agirlik": "cok_agir"}, headers=h
    )
    assert r.status_code == 422, r.text


async def test_kaza_listele_filtre_tur(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await _kaza(kurulu_istemci, h, tur="kaza")
    await _kaza(kurulu_istemci, h, tur="ramak_kala")
    r = await kurulu_istemci.get("/api/v1/is-kazalari?tur=ramak_kala", headers=h)
    assert r.status_code == 200, r.text
    assert all(x["tur"] == "ramak_kala" for x in r.json()["data"])


async def test_risk_olustur_skor_seviye_sunucuda(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _risk(kurulu_istemci, h, olasilik=4, siddet=4)
    assert d["kod"].startswith("RD-")
    assert d["risk_skoru"] == 16
    assert d["risk_seviyesi"] == "cok_yuksek"


async def test_risk_dusuk_seviye(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _risk(kurulu_istemci, h, olasilik=1, siddet=2)
    assert d["risk_skoru"] == 2
    assert d["risk_seviyesi"] == "dusuk"


async def test_risk_gecersiz_olasilik_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/risk-degerlendirmeleri",
        json={"baslik": "X", "olasilik": 6, "siddet": 3},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_risk_guncelle_yeniden_hesap(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _risk(kurulu_istemci, h, olasilik=2, siddet=2)
    assert d["risk_skoru"] == 4
    r = await kurulu_istemci.patch(
        f"/api/v1/risk-degerlendirmeleri/{d['id']}",
        json={"olasilik": 5, "siddet": 3},
        headers=h,
    )
    assert r.status_code == 200, r.text
    g = r.json()["data"]
    assert g["risk_skoru"] == 15
    assert g["risk_seviyesi"] == "yuksek"


async def test_isg_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izl-isg@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izl = _h(
        "alfa",
        await _giris(
            kurulu_istemci,
            {"slug": "alfa", "eposta": "izl-isg@alfa.test", "parola": "Izleyici123!"},
        ),
    )
    # isg:oku var → liste 200
    assert (await kurulu_istemci.get("/api/v1/is-kazalari", headers=izl)).status_code == 200
    # isg:yaz yok → oluştur 403
    r = await kurulu_istemci.post(
        "/api/v1/is-kazalari", json={"tur": "kaza", "agirlik": "orta"}, headers=izl
    )
    assert r.status_code == 403, r.text


async def test_isg_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    da = await _kaza(kurulu_istemci, ha)
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    r = await kurulu_istemci.get(f"/api/v1/is-kazalari/{da['id']}", headers=hb)
    assert r.status_code == 404, r.text
