"""S11 entegrasyon: İK izin talebi onay akışı + ik:onay görev ayrımı + tenant izolasyonu."""

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


async def _personel_id(istemci: AsyncClient, h: dict[str, str], sicil: str) -> int:
    r = await istemci.post(
        "/api/v1/personeller",
        json={"sicil_no": sicil, "ad": "Mehmet", "soyad": "Demir"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _izin(istemci: AsyncClient, h: dict[str, str], personel_id: int, **ek: object) -> dict:
    govde = {
        "personel_id": personel_id,
        "izin_turu": "yillik",
        "baslangic_tarihi": "2026-08-01",
        "bitis_tarihi": "2026-08-05",
        **ek,
    }
    r = await istemci.post("/api/v1/izin-talepleri", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_izin_olustur_oto_kod_gun_sayisi(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    pid = await _personel_id(kurulu_istemci, h, "IZ-P1")
    d = await _izin(kurulu_istemci, h, pid)
    assert d["kod"].startswith("IZ-")
    assert d["durum"] == "taslak"
    assert d["gun_sayisi"] == 5  # 01..05 dâhil


async def test_izin_gecersiz_tur_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    pid = await _personel_id(kurulu_istemci, h, "IZ-P2")
    r = await kurulu_istemci.post(
        "/api/v1/izin-talepleri",
        json={
            "personel_id": pid,
            "izin_turu": "kozmik",
            "baslangic_tarihi": "2026-08-01",
            "bitis_tarihi": "2026-08-02",
        },
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_izin_bitis_baslangictan_once_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    pid = await _personel_id(kurulu_istemci, h, "IZ-P3")
    r = await kurulu_istemci.post(
        "/api/v1/izin-talepleri",
        json={
            "personel_id": pid,
            "baslangic_tarihi": "2026-08-10",
            "bitis_tarihi": "2026-08-05",
        },
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_izin_personel_yok_404(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/izin-talepleri",
        json={
            "personel_id": 999999,
            "baslangic_tarihi": "2026-08-01",
            "bitis_tarihi": "2026-08-02",
        },
        headers=h,
    )
    assert r.status_code == 404, r.text


async def test_izin_akis_gonder_onayla(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    pid = await _personel_id(kurulu_istemci, h, "IZ-P4")
    d = await _izin(kurulu_istemci, h, pid)
    g = await kurulu_istemci.post(f"/api/v1/izin-talepleri/{d['id']}/gonder", headers=h)
    assert g.json()["data"]["durum"] == "onay_bekliyor"
    o = await kurulu_istemci.post(f"/api/v1/izin-talepleri/{d['id']}/onayla", headers=h)
    assert o.status_code == 200, o.text
    veri = o.json()["data"]
    assert veri["durum"] == "onaylandi"
    assert veri["onaylayan_kullanici_id"] is not None


async def test_izin_gecersiz_gecis_409(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    pid = await _personel_id(kurulu_istemci, h, "IZ-P5")
    d = await _izin(kurulu_istemci, h, pid)
    # taslak'ten doğrudan onaylandi yasak (önce gönder gerekli)
    r = await kurulu_istemci.post(f"/api/v1/izin-talepleri/{d['id']}/onayla", headers=h)
    assert r.status_code == 409, r.text


async def test_izin_reddet_neden_zorunlu(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    pid = await _personel_id(kurulu_istemci, h, "IZ-P6")
    d = await _izin(kurulu_istemci, h, pid)
    await kurulu_istemci.post(f"/api/v1/izin-talepleri/{d['id']}/gonder", headers=h)
    bos = await kurulu_istemci.post(
        f"/api/v1/izin-talepleri/{d['id']}/reddet", json={"red_nedeni": ""}, headers=h
    )
    assert bos.status_code == 422, bos.text
    ok = await kurulu_istemci.post(
        f"/api/v1/izin-talepleri/{d['id']}/reddet",
        json={"red_nedeni": "Yoğun dönem"},
        headers=h,
    )
    assert ok.status_code == 200, ok.text
    assert ok.json()["data"]["durum"] == "reddedildi"


async def test_izin_onay_gorev_ayrimi_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    pid = await _personel_id(kurulu_istemci, admin, "IZ-P7")
    # ik rolü: ik:oku + ik:yaz, ONAY YOK
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "ik-uzman@alfa.test", "parola": "IkUzman123!", "roller": ["ik"]},
        headers=admin,
    )
    ik = _h(
        "alfa",
        await _giris(
            kurulu_istemci,
            {"slug": "alfa", "eposta": "ik-uzman@alfa.test", "parola": "IkUzman123!"},
        ),
    )
    d = await _izin(kurulu_istemci, ik, pid)
    # gönder (ik:yaz) çalışır
    g = await kurulu_istemci.post(f"/api/v1/izin-talepleri/{d['id']}/gonder", headers=ik)
    assert g.status_code == 200, g.text
    # onayla (ik:onay) → 403
    r = await kurulu_istemci.post(f"/api/v1/izin-talepleri/{d['id']}/onayla", headers=ik)
    assert r.status_code == 403, r.text


async def test_izin_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    pid = await _personel_id(kurulu_istemci, ha, "IZ-ISO")
    da = await _izin(kurulu_istemci, ha, pid)
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    r = await kurulu_istemci.get(f"/api/v1/izin-talepleri/{da['id']}", headers=hb)
    assert r.status_code == 404, r.text
