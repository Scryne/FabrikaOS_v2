"""S6 entegrasyon testleri: liste uçlarında sunucu-taraflı sıralama + arama.

Sıralama beyaz-listelidir (geçersiz kolon → varsayılana düşer, hata vermez), arama
ILIKE ile kod/metin alanlarında çalışır ve tenant izolasyonunu bozmaz.

NOT: Test veritabanı session-kapsamlıdır (testler arası veri birikir); bu yüzden bu
testler yalnız **kendilerine özgü** benzersiz token'larla (``MAK-SRT``, ``aroni``, ``S6IE``)
filtreleyerek belirleniktir — diğer testlerin kayıtlarıyla çakışmaz.
"""

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


def _baslik(slug: str, access: str) -> dict[str, str]:
    return {"X-Tenant": slug, "Authorization": f"Bearer {access}"}


async def _makine(istemci: AsyncClient, h: dict, kod: str, ad: str) -> int:
    r = await istemci.post("/api/v1/makineler", json={"kod": kod, "ad": ad}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


async def test_makine_siralama_arama_ve_gecersiz_fallback(kurulu_istemci: AsyncClient) -> None:
    access = await _giris(kurulu_istemci, ALFA)
    h = _baslik("alfa", access)
    for kod, ad in [
        ("MAK-SRT-Z", "Pres s6srt zeta"),
        ("MAK-SRT-A", "Enjeksiyon s6srt aroni"),
        ("MAK-SRT-M", "Kaynak s6srt"),
    ]:
        await _makine(kurulu_istemci, h, kod, ad)

    # kod artan (arama=MAK-SRT → yalnız bu testin makineleri)
    r = await kurulu_istemci.get("/api/v1/makineler?siralama=kod&yon=asc&arama=MAK-SRT", headers=h)
    assert r.status_code == 200
    assert [m["kod"] for m in r.json()["data"]] == ["MAK-SRT-A", "MAK-SRT-M", "MAK-SRT-Z"]

    # kod azalan
    r = await kurulu_istemci.get("/api/v1/makineler?siralama=kod&yon=desc&arama=MAK-SRT", headers=h)
    assert [m["kod"] for m in r.json()["data"]] == ["MAK-SRT-Z", "MAK-SRT-M", "MAK-SRT-A"]

    # ad üzerinde büyük/küçük harf duyarsız arama ("ARONI" → "aroni")
    r = await kurulu_istemci.get("/api/v1/makineler?arama=ARONI", headers=h)
    assert [m["kod"] for m in r.json()["data"]] == ["MAK-SRT-A"]

    # geçersiz sıralama kolonu → 200, varsayılana düşer (hata yok)
    r = await kurulu_istemci.get("/api/v1/makineler?siralama=DROP&arama=MAK-SRT", headers=h)
    assert r.status_code == 200
    assert {m["kod"] for m in r.json()["data"]} == {"MAK-SRT-A", "MAK-SRT-M", "MAK-SRT-Z"}


async def test_isemri_arama_ve_siralama(kurulu_istemci: AsyncClient) -> None:
    access = await _giris(kurulu_istemci, ALFA)
    h = _baslik("alfa", access)
    mid = await _makine(kurulu_istemci, h, "MAK-IE-LISTE", "Is emri makinesi")

    for baslik, oncelik in [
        ("S6IE Rulman degisimi", "dusuk"),
        ("S6IE Yag kacagi onarimi", "kritik"),
        ("S6IE Sensor kalibrasyonu", "orta"),
    ]:
        r = await kurulu_istemci.post(
            "/api/v1/is-emirleri",
            json={"baslik": baslik, "makine_id": mid, "oncelik": oncelik},
            headers=h,
        )
        assert r.status_code == 201, r.text

    # başlık üzerinde arama (benzersiz token)
    r = await kurulu_istemci.get("/api/v1/is-emirleri?arama=kacagi", headers=h)
    assert r.status_code == 200
    assert [e["baslik"] for e in r.json()["data"]] == ["S6IE Yag kacagi onarimi"]

    # başlık artan sıralama (arama=S6IE → yalnız bu testin emirleri)
    r = await kurulu_istemci.get(
        "/api/v1/is-emirleri?arama=S6IE&siralama=baslik&yon=asc", headers=h
    )
    assert [e["baslik"] for e in r.json()["data"]] == [
        "S6IE Rulman degisimi",
        "S6IE Sensor kalibrasyonu",
        "S6IE Yag kacagi onarimi",
    ]


async def test_liste_arama_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    access_alfa = await _giris(kurulu_istemci, ALFA)
    await _makine(kurulu_istemci, _baslik("alfa", access_alfa), "MAK-GIZLI-S6", "Gizli s6 kayit")

    # Beta'da aynı arama 0 sonuç (cross-tenant sızıntı yok).
    access_beta = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.get(
        "/api/v1/makineler?arama=GIZLI-S6", headers=_baslik("beta", access_beta)
    )
    assert r.status_code == 200
    assert r.json()["data"] == []
    assert r.json()["meta"]["toplam"] == 0
