"""S9 entegrasyon: çok-kalemli satınalma talebi + onay akışı + satinalma:onay ayrımı + izolasyon."""

from __future__ import annotations

import re

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


async def _malzeme_id(istemci: AsyncClient, h: dict[str, str], kod: str) -> int:
    r = await istemci.post(
        "/api/v1/malzemeler", json={"kod": kod, "ad": kod, "birim": "adet"}, headers=h
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _talep(
    istemci: AsyncClient, h: dict[str, str], mid: int, fiyat: float | None = 100
) -> dict:
    govde = {
        "baslik": "Rulman alımı",
        "kalemler": [
            {"malzeme_id": mid, "miktar": 3, "birim": "adet", "tahmini_birim_fiyat": fiyat}
        ],
    }
    r = await istemci.post("/api/v1/satinalma-talepleri", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_talep_olustur_oto_kod_ve_toplam(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-ST1")
    d = await _talep(kurulu_istemci, h, mid, fiyat=100)
    assert d["durum"] == "taslak"
    assert re.fullmatch(r"ST-\d{4}-\d{6}", d["kod"]), d["kod"]
    # detay: tahmini_toplam = 3 * 100
    r = await kurulu_istemci.get(f"/api/v1/satinalma-talepleri/{d['id']}", headers=h)
    assert r.json()["data"]["tahmini_toplam"] == 300
    assert len(r.json()["data"]["kalemler"]) == 1


async def test_talep_bos_kalem_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/satinalma-talepleri", json={"baslik": "Boş", "kalemler": []}, headers=h
    )
    assert r.status_code == 422, r.text


async def test_akis_gonder_onayla(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-ST2")
    d = await _talep(kurulu_istemci, h, mid)
    tid = d["id"]
    assert (
        await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{tid}/gonder", headers=h)
    ).status_code == 200
    r = await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{tid}/onayla", headers=h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["durum"] == "onaylandi"
    assert r.json()["data"]["onaylayan_kullanici_id"] is not None


async def test_gecersiz_gecis_409(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-ST3")
    d = await _talep(kurulu_istemci, h, mid)
    # taslak → onayla (önce gönderilmeli) yasak
    r = await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{d['id']}/onayla", headers=h)
    assert r.status_code == 409, r.text


async def test_reddet_neden_gerekli_ve_calisir(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, h, "MLZ-ST4")
    d = await _talep(kurulu_istemci, h, mid)
    tid = d["id"]
    await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{tid}/gonder", headers=h)
    # neden yok → 422
    assert (
        await kurulu_istemci.post(
            f"/api/v1/satinalma-talepleri/{tid}/reddet", json={"red_nedeni": ""}, headers=h
        )
    ).status_code == 422
    r = await kurulu_istemci.post(
        f"/api/v1/satinalma-talepleri/{tid}/reddet", json={"red_nedeni": "Bütçe yok"}, headers=h
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["durum"] == "reddedildi"
    assert r.json()["data"]["red_nedeni"] == "Bütçe yok"


async def test_onay_ayri_izin_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, admin, "MLZ-ST5")
    # 'depo' rolü: satinalma:yaz var ama satinalma:onay YOK (Task 6'da seed edilir).
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "depo@alfa.test", "parola": "Depo12345!", "roller": ["depo"]},
        headers=admin,
    )
    depo = _h(
        "alfa",
        await _giris(
            kurulu_istemci, {"slug": "alfa", "eposta": "depo@alfa.test", "parola": "Depo12345!"}
        ),
    )
    d = await _talep(kurulu_istemci, depo, mid)
    tid = d["id"]
    assert (
        await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{tid}/gonder", headers=depo)
    ).status_code == 200
    # satinalma:onay yok → 403
    r = await kurulu_istemci.post(f"/api/v1/satinalma-talepleri/{tid}/onayla", headers=depo)
    assert r.status_code == 403, r.text


async def test_talep_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _malzeme_id(kurulu_istemci, ha, "MLZ-ST6")
    d = await _talep(kurulu_istemci, ha, mid)
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    assert (
        await kurulu_istemci.get(f"/api/v1/satinalma-talepleri/{d['id']}", headers=hb)
    ).status_code == 404
