"""S12 entegrasyon: ticari özet (pano) — sayaçlar + yaklaşan sözleşmeler + RBAC/izolasyon."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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


async def test_ticari_ozet_sayaclar(kurulu_istemci: AsyncClient) -> None:
    h = _h("beta", await _giris(kurulu_istemci, BETA))  # beta izole (temiz sayaç)
    # firma + yaklaşan aktif sözleşme + açık talep + yayınlı duyuru
    fr = await kurulu_istemci.post("/api/v1/firmalar", json={"ad": "Ozet Firma"}, headers=h)
    fid = fr.json()["data"]["id"]
    yakin = (datetime.now(UTC).date() + timedelta(days=15)).isoformat()
    sr = await kurulu_istemci.post(
        "/api/v1/sozlesmeler",
        json={
            "firma_id": fid,
            "baslik": "Yaklaşan",
            "baslangic_tarihi": "2026-01-01",
            "bitis_tarihi": yakin,
        },
        headers=h,
    )
    sid = sr.json()["data"]["id"]
    await kurulu_istemci.patch(
        f"/api/v1/sozlesmeler/{sid}/durum", json={"durum": "aktif"}, headers=h
    )
    await kurulu_istemci.post("/api/v1/talepler", json={"baslik": "Açık talep"}, headers=h)
    dr = await kurulu_istemci.post("/api/v1/duyurular", json={"baslik": "Duyuru"}, headers=h)
    await kurulu_istemci.post(f"/api/v1/duyurular/{dr.json()['data']['id']}/yayinla", headers=h)

    r = await kurulu_istemci.get("/api/v1/ticari/ozet", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    s = veri["sayaclar"]
    assert s["firma_sayisi"] >= 1
    assert s["aktif_sozlesme"] >= 1
    assert s["yaklasan_sozlesme"] >= 1
    assert s["acik_talep"] >= 1
    assert s["yayinli_duyuru"] >= 1
    assert any(x["id"] == sid for x in veri["yaklasan_sozlesmeler"])
    assert any(x["baslik"] == "Duyuru" for x in veri["son_duyurular"])


async def test_ticari_ozet_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "dok@alfa.test", "parola": "Dokuman123!", "roller": ["dokuman"]},
        headers=admin,
    )
    dok = _h(
        "alfa",
        await _giris(
            kurulu_istemci,
            {"slug": "alfa", "eposta": "dok@alfa.test", "parola": "Dokuman123!"},
        ),
    )
    # dokuman rolü crm:oku içermez → 403
    r = await kurulu_istemci.get("/api/v1/ticari/ozet", headers=dok)
    assert r.status_code == 403, r.text
