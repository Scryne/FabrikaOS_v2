"""S11 entegrasyon: İK personel özlük + KVKK (TC maskeleme + ik:oku erişim) + tenant izolasyonu."""

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


async def _personel(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"sicil_no": "P-001", "ad": "Ayşe", "soyad": "Yılmaz", "departman": "Üretim", **ek}
    r = await istemci.post("/api/v1/personeller", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_personel_olustur(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _personel(kurulu_istemci, h)
    assert d["sicil_no"] == "P-001"
    assert d["ad"] == "Ayşe"
    assert d["aktif"] is True


async def test_personel_tc_maskeli(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _personel(kurulu_istemci, h, sicil_no="P-TC", tc_kimlik_no="12345678901")
    # KVKK: TC kimlik yanıtta maskeli döner (yalnız son 2 hane).
    assert d["tc_kimlik_no"] == "*********01"
    assert "12345678901" not in str(d)


async def test_personel_sicil_tekil_409(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await _personel(kurulu_istemci, h, sicil_no="P-DUP")
    r = await kurulu_istemci.post(
        "/api/v1/personeller",
        json={"sicil_no": "P-DUP", "ad": "X", "soyad": "Y"},
        headers=h,
    )
    assert r.status_code == 409, r.text


async def test_personel_listele_filtre_departman(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await _personel(kurulu_istemci, h, sicil_no="P-U1", departman="Üretim")
    await _personel(kurulu_istemci, h, sicil_no="P-K1", departman="Kalite")
    r = await kurulu_istemci.get("/api/v1/personeller?departman=Kalite", headers=h)
    assert r.status_code == 200, r.text
    assert all(x["departman"] == "Kalite" for x in r.json()["data"])


async def test_personel_guncelle(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    d = await _personel(kurulu_istemci, h, sicil_no="P-G1")
    r = await kurulu_istemci.patch(
        f"/api/v1/personeller/{d['id']}", json={"unvan": "Vardiya Amiri", "aktif": False}, headers=h
    )
    assert r.status_code == 200, r.text
    g = r.json()["data"]
    assert g["unvan"] == "Vardiya Amiri"
    assert g["aktif"] is False


async def test_personel_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izl-ik@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izl = _h(
        "alfa",
        await _giris(
            kurulu_istemci,
            {"slug": "alfa", "eposta": "izl-ik@alfa.test", "parola": "Izleyici123!"},
        ),
    )
    # ik:oku var → liste 200 (erişim kısıtı: yalnız yetkili görebilir)
    assert (await kurulu_istemci.get("/api/v1/personeller", headers=izl)).status_code == 200
    # ik:yaz yok → oluştur 403
    r = await kurulu_istemci.post(
        "/api/v1/personeller", json={"sicil_no": "P-X", "ad": "A", "soyad": "B"}, headers=izl
    )
    assert r.status_code == 403, r.text


async def test_personel_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    da = await _personel(kurulu_istemci, ha, sicil_no="P-ISO")
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    r = await kurulu_istemci.get(f"/api/v1/personeller/{da['id']}", headers=hb)
    assert r.status_code == 404, r.text
