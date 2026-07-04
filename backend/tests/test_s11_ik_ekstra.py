"""S11 entegrasyon: İK fazla mesai + zimmet (iade) + sertifika."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import ALFA

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


async def _personel_id(istemci: AsyncClient, h: dict[str, str], sicil: str) -> int:
    r = await istemci.post(
        "/api/v1/personeller",
        json={"sicil_no": sicil, "ad": "Zeynep", "soyad": "Kaya"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def test_fazla_mesai_olustur_onayla(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    pid = await _personel_id(kurulu_istemci, h, "FM-P1")
    r = await kurulu_istemci.post(
        "/api/v1/fazla-mesailer",
        json={"personel_id": pid, "tarih": "2026-08-01", "saat": 3.5, "aciklama": "Sevkiyat"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    m = r.json()["data"]
    assert m["saat"] == 3.5
    assert m["onayli"] is False
    o = await kurulu_istemci.post(f"/api/v1/fazla-mesailer/{m['id']}/onayla", headers=h)
    assert o.status_code == 200, o.text
    assert o.json()["data"]["onayli"] is True


async def test_fazla_mesai_personel_yok_404(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/fazla-mesailer",
        json={"personel_id": 999999, "tarih": "2026-08-01", "saat": 2},
        headers=h,
    )
    assert r.status_code == 404, r.text


async def test_zimmet_olustur_iade(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    pid = await _personel_id(kurulu_istemci, h, "ZM-P1")
    r = await kurulu_istemci.post(
        "/api/v1/zimmetler",
        json={
            "personel_id": pid,
            "demirbas": "Dizüstü Bilgisayar",
            "seri_no": "SN-123",
            "zimmet_tarihi": "2026-07-01",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    z = r.json()["data"]
    assert z["durum"] == "zimmetli"
    assert z["iade_tarihi"] is None
    iade = await kurulu_istemci.post(f"/api/v1/zimmetler/{z['id']}/iade", headers=h)
    assert iade.status_code == 200, iade.text
    veri = iade.json()["data"]
    assert veri["durum"] == "iade_edildi"
    assert veri["iade_tarihi"] is not None
    # ikinci iade → 409
    tekrar = await kurulu_istemci.post(f"/api/v1/zimmetler/{z['id']}/iade", headers=h)
    assert tekrar.status_code == 409, tekrar.text


async def test_zimmet_listele_filtre_durum(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    pid = await _personel_id(kurulu_istemci, h, "ZM-P2")
    for i in range(2):
        await kurulu_istemci.post(
            "/api/v1/zimmetler",
            json={"personel_id": pid, "demirbas": f"Alet {i}", "zimmet_tarihi": "2026-07-01"},
            headers=h,
        )
    r = await kurulu_istemci.get(f"/api/v1/zimmetler?personel_id={pid}&durum=zimmetli", headers=h)
    assert r.status_code == 200, r.text
    assert all(x["durum"] == "zimmetli" for x in r.json()["data"])


async def test_sertifika_olustur_listele(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    pid = await _personel_id(kurulu_istemci, h, "ST-P1")
    r = await kurulu_istemci.post(
        "/api/v1/sertifikalar",
        json={
            "personel_id": pid,
            "ad": "İSG Temel Eğitimi",
            "kurum": "OSGB",
            "alinma_tarihi": "2026-01-15",
            "gecerlilik_tarihi": "2028-01-15",
        },
        headers=h,
    )
    assert r.status_code == 201, r.text
    assert r.json()["data"]["ad"] == "İSG Temel Eğitimi"
    liste = await kurulu_istemci.get(f"/api/v1/sertifikalar?personel_id={pid}", headers=h)
    assert liste.status_code == 200, liste.text
    assert liste.json()["meta"]["toplam"] == 1
