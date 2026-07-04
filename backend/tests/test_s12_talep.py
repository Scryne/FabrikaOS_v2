"""S12 entegrasyon: talep — oto kod, durum makinesi, atama, RBAC, tenant izolasyonu."""

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


async def _talep(istemci: AsyncClient, h: dict[str, str], **ek: object) -> dict:
    govde = {"baslik": "Teklif isteği", "tur": "teklif", "oncelik": "yuksek", **ek}
    r = await istemci.post("/api/v1/talepler", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_talep_oto_kod_talep_eden(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    t = await _talep(kurulu_istemci, h)
    assert t["kod"].startswith("TL-")
    assert t["durum"] == "acik"
    assert t["talep_eden_kullanici_id"] is not None


async def test_talep_gecersiz_oncelik_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/talepler", json={"baslik": "X", "oncelik": "acil"}, headers=h
    )
    assert r.status_code == 422, r.text


async def test_talep_durum_akisi(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    t = await _talep(kurulu_istemci, h)
    for hedef in ("inceleniyor", "cozuldu", "kapandi"):
        r = await kurulu_istemci.patch(
            f"/api/v1/talepler/{t['id']}/durum", json={"durum": hedef}, headers=h
        )
        assert r.status_code == 200, r.text
        assert r.json()["data"]["durum"] == hedef
    # kapandi terminal → iptal yasak
    r2 = await kurulu_istemci.patch(
        f"/api/v1/talepler/{t['id']}/durum", json={"durum": "iptal"}, headers=h
    )
    assert r2.status_code == 409, r2.text


async def test_talep_yeniden_ac(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    t = await _talep(kurulu_istemci, h)
    await kurulu_istemci.patch(
        f"/api/v1/talepler/{t['id']}/durum", json={"durum": "inceleniyor"}, headers=h
    )
    await kurulu_istemci.patch(
        f"/api/v1/talepler/{t['id']}/durum", json={"durum": "cozuldu"}, headers=h
    )
    # cozuldu -> inceleniyor (yeniden aç)
    r = await kurulu_istemci.patch(
        f"/api/v1/talepler/{t['id']}/durum", json={"durum": "inceleniyor"}, headers=h
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["durum"] == "inceleniyor"


async def test_talep_gecersiz_gecis_409(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    t = await _talep(kurulu_istemci, h)
    # acik -> cozuldu doğrudan yasak
    r = await kurulu_istemci.patch(
        f"/api/v1/talepler/{t['id']}/durum", json={"durum": "cozuldu"}, headers=h
    )
    assert r.status_code == 409, r.text


async def test_talep_ata_ve_filtrele(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    # atama için ikinci kullanıcı
    r = await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "cozumleyici@alfa.test", "parola": "Cozumci123!", "roller": ["crm"]},
        headers=admin,
    )
    atanan_id = int(r.json()["data"]["id"])
    t = await _talep(kurulu_istemci, admin)
    r2 = await kurulu_istemci.patch(
        f"/api/v1/talepler/{t['id']}", json={"atanan_kullanici_id": atanan_id}, headers=admin
    )
    assert r2.json()["data"]["atanan_kullanici_id"] == atanan_id
    liste = await kurulu_istemci.get(
        f"/api/v1/talepler?atanan_kullanici_id={atanan_id}", headers=admin
    )
    assert liste.json()["meta"]["toplam"] == 1


async def test_talep_firma_yok_404(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/talepler", json={"baslik": "X", "firma_id": 999999}, headers=h
    )
    assert r.status_code == 404, r.text


async def test_talep_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    ta = await _talep(kurulu_istemci, ha)
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    r = await kurulu_istemci.get(f"/api/v1/talepler/{ta['id']}", headers=hb)
    assert r.status_code == 404, r.text
