"""S4 entegrasyon testleri: iş emri yaşam döngüsü + durum makinesi + outbox olayı,
yorum, bakım planı CRUD, RBAC ve tenant izolasyonu.

Outbox (``giden_olaylar``) doğrulaması için tenant şemasına asyncpg ile doğrudan bakılır
(uygulama kodu değil, test introspection'ı — sabit şema öneki burada serbesttir).
"""

from __future__ import annotations

import json
import re

import asyncpg
from httpx import AsyncClient

from tests.conftest import ALFA, BETA

KIMLIK = "/api/v1/kimlik"
ASYNCPG_URL = "postgresql://fabrikaos:fabrikaos@localhost:5432/fabrikaos_test"


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


async def _ben_id(istemci: AsyncClient, h: dict[str, str]) -> int:
    r = await istemci.get(f"{KIMLIK}/ben", headers=h)
    assert r.status_code == 200, r.text
    return int(r.json()["data"]["id"])


async def _makine_olustur(istemci: AsyncClient, h: dict[str, str], kod: str) -> int:
    r = await istemci.post("/api/v1/makineler", json={"kod": kod, "ad": kod}, headers=h)
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _outbox_govdeleri(sema: str, olay_turu: str) -> list[dict]:
    c = await asyncpg.connect(ASYNCPG_URL)
    try:
        rows = await c.fetch(
            f'SELECT govde FROM "{sema}".giden_olaylar WHERE olay_turu = $1 ORDER BY id',
            olay_turu,
        )
        return [json.loads(r["govde"]) if isinstance(r["govde"], str) else r["govde"] for r in rows]
    finally:
        await c.close()


# --- İş emri oluşturma ---
async def test_is_emri_olustur_oto_kod(kurulu_istemci: AsyncClient) -> None:
    h = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, h, "MAK-IE1")

    # kod verilmedi → sunucu IE-{yıl}-{id:06d} üretir.
    r = await kurulu_istemci.post(
        "/api/v1/is-emirleri", json={"baslik": "Rulman değişimi", "makine_id": mid}, headers=h
    )
    assert r.status_code == 201, r.text
    d = r.json()["data"]
    assert d["durum"] == "acik"
    assert d["oncelik"] == "orta"
    assert re.fullmatch(r"IE-\d{4}-\d{6}", d["kod"]), d["kod"]


async def test_is_emri_kod_cakismasi_409(kurulu_istemci: AsyncClient) -> None:
    h = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, h, "MAK-IE2")
    govde = {"baslik": "İş", "makine_id": mid, "kod": "IE-EL-001"}
    ilk = await kurulu_istemci.post("/api/v1/is-emirleri", json=govde, headers=h)
    assert ilk.status_code == 201, ilk.text
    r = await kurulu_istemci.post("/api/v1/is-emirleri", json=govde, headers=h)
    assert r.status_code == 409, r.text


async def test_is_emri_makine_yok_404(kurulu_istemci: AsyncClient) -> None:
    h = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/is-emirleri", json={"baslik": "İş", "makine_id": 999999}, headers=h
    )
    assert r.status_code == 404, r.text


async def test_is_emri_gecersiz_oncelik_422(kurulu_istemci: AsyncClient) -> None:
    h = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, h, "MAK-IE3")
    r = await kurulu_istemci.post(
        "/api/v1/is-emirleri",
        json={"baslik": "İş", "makine_id": mid, "oncelik": "acil"},
        headers=h,
    )
    assert r.status_code == 422, r.text


# --- Yaşam döngüsü + outbox olayı ---
async def test_yasam_dongusu_ac_ata_ilerle_kapat_ve_olay(kurulu_istemci: AsyncClient) -> None:
    h = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    benim_id = await _ben_id(kurulu_istemci, h)
    mid = await _makine_olustur(kurulu_istemci, h, "MAK-DONGU")
    iid = (
        await kurulu_istemci.post(
            "/api/v1/is-emirleri", json={"baslik": "Bakım", "makine_id": mid}, headers=h
        )
    ).json()["data"]["id"]

    # acik → atandi (atanan zorunlu)
    r = await kurulu_istemci.patch(
        f"/api/v1/is-emirleri/{iid}/durum",
        json={"durum": "atandi", "atanan_kullanici_id": benim_id},
        headers=h,
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["durum"] == "atandi"
    assert r.json()["data"]["atanan_kullanici_id"] == benim_id

    # atandi → devam_ediyor
    r = await kurulu_istemci.patch(
        f"/api/v1/is-emirleri/{iid}/durum", json={"durum": "devam_ediyor"}, headers=h
    )
    assert r.status_code == 200, r.text

    # devam_ediyor → kapandi (kapanış tarihi + olay)
    r = await kurulu_istemci.patch(
        f"/api/v1/is-emirleri/{iid}/durum", json={"durum": "kapandi"}, headers=h
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["kapanis_tarihi"] is not None

    # Outbox: is_emri.kapandi olayı bu iş emri için yazılmış olmalı.
    govdeler = await _outbox_govdeleri("tenant_alfa", "is_emri.kapandi")
    assert any(g.get("is_emri_id") == iid for g in govdeler), govdeler


async def test_atamasiz_atandi_422(kurulu_istemci: AsyncClient) -> None:
    h = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, h, "MAK-ATAMASIZ")
    iid = (
        await kurulu_istemci.post(
            "/api/v1/is-emirleri", json={"baslik": "İş", "makine_id": mid}, headers=h
        )
    ).json()["data"]["id"]
    # atanan yok → 422
    r = await kurulu_istemci.patch(
        f"/api/v1/is-emirleri/{iid}/durum", json={"durum": "atandi"}, headers=h
    )
    assert r.status_code == 422, r.text


async def test_gecersiz_gecis_409(kurulu_istemci: AsyncClient) -> None:
    h = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, h, "MAK-GECERSIZ")
    iid = (
        await kurulu_istemci.post(
            "/api/v1/is-emirleri", json={"baslik": "İş", "makine_id": mid}, headers=h
        )
    ).json()["data"]["id"]
    # acik → kapandi atlamalı geçiş yasak
    r = await kurulu_istemci.patch(
        f"/api/v1/is-emirleri/{iid}/durum", json={"durum": "kapandi"}, headers=h
    )
    assert r.status_code == 409, r.text


async def test_terminal_durumdan_gecis_409(kurulu_istemci: AsyncClient) -> None:
    h = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, h, "MAK-IPTAL")
    iid = (
        await kurulu_istemci.post(
            "/api/v1/is-emirleri", json={"baslik": "İş", "makine_id": mid}, headers=h
        )
    ).json()["data"]["id"]
    # acik → iptal (terminal)
    assert (
        await kurulu_istemci.patch(
            f"/api/v1/is-emirleri/{iid}/durum", json={"durum": "iptal"}, headers=h
        )
    ).status_code == 200
    # iptal → devam_ediyor yasak
    r = await kurulu_istemci.patch(
        f"/api/v1/is-emirleri/{iid}/durum", json={"durum": "devam_ediyor"}, headers=h
    )
    assert r.status_code == 409, r.text


# --- Liste/filtre + yorum ---
async def test_liste_filtre_durum(kurulu_istemci: AsyncClient) -> None:
    h = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, h, "MAK-LISTE")
    for _ in range(2):
        await kurulu_istemci.post(
            "/api/v1/is-emirleri", json={"baslik": "İş", "makine_id": mid}, headers=h
        )
    r = await kurulu_istemci.get("/api/v1/is-emirleri?durum=acik", headers=h)
    assert r.status_code == 200
    assert all(d["durum"] == "acik" for d in r.json()["data"])
    assert "meta" in r.json()


async def test_yorum_ekle_ve_detayda_gorunur(kurulu_istemci: AsyncClient) -> None:
    h = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, h, "MAK-YORUM")
    iid = (
        await kurulu_istemci.post(
            "/api/v1/is-emirleri", json={"baslik": "İş", "makine_id": mid}, headers=h
        )
    ).json()["data"]["id"]
    r = await kurulu_istemci.post(
        f"/api/v1/is-emirleri/{iid}/yorum", json={"metin": "Parça sipariş edildi"}, headers=h
    )
    assert r.status_code == 201, r.text

    r = await kurulu_istemci.get(f"/api/v1/is-emirleri/{iid}", headers=h)
    assert r.status_code == 200
    metinler = [y["metin"] for y in r.json()["data"]["yorumlar"]]
    assert "Parça sipariş edildi" in metinler


# --- RBAC ---
async def test_isemri_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, admin, "MAK-RBAC")
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izl-ie@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izl = _baslik(
        "alfa",
        await _giris(
            kurulu_istemci,
            {"slug": "alfa", "eposta": "izl-ie@alfa.test", "parola": "Izleyici123!"},
        ),
    )
    # isemri:oku var → listele 200
    assert (await kurulu_istemci.get("/api/v1/is-emirleri", headers=izl)).status_code == 200
    # isemri:yaz yok → oluştur 403
    r = await kurulu_istemci.post(
        "/api/v1/is-emirleri", json={"baslik": "İş", "makine_id": mid}, headers=izl
    )
    assert r.status_code == 403, r.text


# --- Tenant izolasyonu ---
async def test_isemri_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, ha, "MAK-IZOLE-IE")
    iid = (
        await kurulu_istemci.post(
            "/api/v1/is-emirleri",
            json={"baslik": "Gizli", "makine_id": mid, "kod": "IE-GIZLI-A"},
            headers=ha,
        )
    ).json()["data"]["id"]

    hb = _baslik("beta", await _giris(kurulu_istemci, BETA))
    # Listede görünmez
    r = await kurulu_istemci.get("/api/v1/is-emirleri", headers=hb)
    assert "IE-GIZLI-A" not in [d["kod"] for d in r.json()["data"]]
    # Doğrudan id ile erişilemez (görünmez → 404)
    assert (await kurulu_istemci.get(f"/api/v1/is-emirleri/{iid}", headers=hb)).status_code == 404


# --- Bakım planları ---
async def test_bakim_plani_crud(kurulu_istemci: AsyncClient) -> None:
    h = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, h, "MAK-BAKIM")
    r = await kurulu_istemci.post(
        "/api/v1/bakim-planlari",
        json={"makine_id": mid, "ad": "Aylık yağlama", "tip": "periyodik", "periyot_gun": 30},
        headers=h,
    )
    assert r.status_code == 201, r.text
    bid = r.json()["data"]["id"]
    assert r.json()["data"]["aktif"] is True

    # detay
    assert (await kurulu_istemci.get(f"/api/v1/bakim-planlari/{bid}", headers=h)).status_code == 200
    # güncelle (pasifleştir)
    r = await kurulu_istemci.patch(
        f"/api/v1/bakim-planlari/{bid}", json={"aktif": False}, headers=h
    )
    assert r.status_code == 200
    assert r.json()["data"]["aktif"] is False
    # liste
    r = await kurulu_istemci.get("/api/v1/bakim-planlari", headers=h)
    assert r.status_code == 200
    assert bid in [b["id"] for b in r.json()["data"]]


async def test_bakim_gecersiz_tip_422(kurulu_istemci: AsyncClient) -> None:
    h = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, h, "MAK-BAKIM2")
    r = await kurulu_istemci.post(
        "/api/v1/bakim-planlari",
        json={"makine_id": mid, "ad": "Plan", "tip": "sihirli"},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_bakim_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _baslik("alfa", await _giris(kurulu_istemci, ALFA))
    mid = await _makine_olustur(kurulu_istemci, admin, "MAK-BAKIM-RBAC")
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izl-bk@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izl = _baslik(
        "alfa",
        await _giris(
            kurulu_istemci,
            {"slug": "alfa", "eposta": "izl-bk@alfa.test", "parola": "Izleyici123!"},
        ),
    )
    assert (await kurulu_istemci.get("/api/v1/bakim-planlari", headers=izl)).status_code == 200
    r = await kurulu_istemci.post(
        "/api/v1/bakim-planlari", json={"makine_id": mid, "ad": "Olmaz"}, headers=izl
    )
    assert r.status_code == 403, r.text
