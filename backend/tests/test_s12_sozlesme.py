"""S12 entegrasyon: sözleşme — oto kod, durum makinesi, yaklaşan tarama (outbox), izolasyon."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import asyncpg
from httpx import AsyncClient

from tests.conftest import ALFA, BETA, TEST_URL

KIMLIK = "/api/v1/kimlik"
_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")


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


async def _firma(istemci: AsyncClient, h: dict[str, str], ad: str) -> int:
    r = await istemci.post("/api/v1/firmalar", json={"ad": ad}, headers=h)
    assert r.status_code == 201, r.text
    return int(r.json()["data"]["id"])


async def _sozlesme(istemci: AsyncClient, h: dict[str, str], firma_id: int, **ek: object) -> dict:
    govde = {
        "firma_id": firma_id,
        "baslik": "Bakım Sözleşmesi",
        "tur": "hizmet",
        "baslangic_tarihi": "2026-01-01",
        "bitis_tarihi": "2026-12-31",
        **ek,
    }
    r = await istemci.post("/api/v1/sozlesmeler", json=govde, headers=h)
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_sozlesme_oto_kod(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    fid = await _firma(kurulu_istemci, h, "Sözleşmeli Firma")
    s = await _sozlesme(kurulu_istemci, h, fid, tutar="15000.50")
    assert s["kod"].startswith("SZ-")
    assert s["durum"] == "taslak"
    assert s["tutar"] == 15000.5


async def test_sozlesme_gecersiz_tur_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    fid = await _firma(kurulu_istemci, h, "F2")
    r = await kurulu_istemci.post(
        "/api/v1/sozlesmeler",
        json={
            "firma_id": fid,
            "baslik": "X",
            "tur": "uzay",
            "baslangic_tarihi": "2026-01-01",
            "bitis_tarihi": "2026-02-01",
        },
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_sozlesme_firma_yok_404(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    r = await kurulu_istemci.post(
        "/api/v1/sozlesmeler",
        json={
            "firma_id": 999999,
            "baslik": "X",
            "baslangic_tarihi": "2026-01-01",
            "bitis_tarihi": "2026-02-01",
        },
        headers=h,
    )
    assert r.status_code == 404, r.text


async def test_sozlesme_durum_akisi(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    fid = await _firma(kurulu_istemci, h, "Durum Firma")
    s = await _sozlesme(kurulu_istemci, h, fid)
    # taslak -> aktif
    r = await kurulu_istemci.patch(
        f"/api/v1/sozlesmeler/{s['id']}/durum", json={"durum": "aktif"}, headers=h
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["durum"] == "aktif"
    # aktif -> feshedildi
    r2 = await kurulu_istemci.patch(
        f"/api/v1/sozlesmeler/{s['id']}/durum", json={"durum": "feshedildi"}, headers=h
    )
    assert r2.json()["data"]["durum"] == "feshedildi"
    # terminal -> aktif yasak
    r3 = await kurulu_istemci.patch(
        f"/api/v1/sozlesmeler/{s['id']}/durum", json={"durum": "aktif"}, headers=h
    )
    assert r3.status_code == 409, r3.text


async def test_sozlesme_gecersiz_durum_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    fid = await _firma(kurulu_istemci, h, "Geçersiz Durum")
    s = await _sozlesme(kurulu_istemci, h, fid)
    r = await kurulu_istemci.patch(
        f"/api/v1/sozlesmeler/{s['id']}/durum", json={"durum": "kozmik"}, headers=h
    )
    assert r.status_code == 422, r.text


async def _outbox_sayisi(slug: str) -> int:
    conn = await asyncpg.connect(_DSN)
    try:
        await conn.execute(f'SET search_path TO "tenant_{slug}", public')
        return int(
            await conn.fetchval(
                "SELECT count(*) FROM giden_olaylar WHERE olay_turu = 'sozlesme.yaklasiyor'"
            )
        )
    finally:
        await conn.close()


async def test_yaklasan_tara_kenar_tetik(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    fid = await _firma(kurulu_istemci, h, "Yaklaşan Firma")
    bugun = datetime.now(UTC).date()
    yakin = (bugun + timedelta(days=10)).isoformat()
    s = await _sozlesme(
        kurulu_istemci, h, fid, baslangic_tarihi="2026-01-01", bitis_tarihi=yakin
    )
    # aktif olmalı ki yaklaşan sayılsın
    await kurulu_istemci.patch(
        f"/api/v1/sozlesmeler/{s['id']}/durum", json={"durum": "aktif"}, headers=h
    )
    onceki = await _outbox_sayisi("alfa")
    # yaklaşan listesinde görünür
    yak = await kurulu_istemci.get("/api/v1/sozlesmeler/yaklasan?esik_gun=30", headers=h)
    assert any(x["id"] == s["id"] for x in yak.json()["data"])
    # tara → 1 olay, ikinci tara → 0 (kenar-tetik, bir kez)
    t1 = await kurulu_istemci.post(
        "/api/v1/sozlesmeler/yaklasanlari-tara", json={"esik_gun": 30}, headers=h
    )
    assert t1.json()["data"]["islenen"] >= 1
    t2 = await kurulu_istemci.post(
        "/api/v1/sozlesmeler/yaklasanlari-tara", json={"esik_gun": 30}, headers=h
    )
    assert t2.json()["data"]["islenen"] == 0
    assert await _outbox_sayisi("alfa") == onceki + 1
    # bayrak işaretlendi
    det = await kurulu_istemci.get(f"/api/v1/sozlesmeler/{s['id']}", headers=h)
    assert det.json()["data"]["yaklasim_bildirildi"] is True


async def test_sozlesme_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    fid = await _firma(kurulu_istemci, admin, "RBAC Firma")
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izle2@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izle = _h(
        "alfa",
        await _giris(
            kurulu_istemci,
            {"slug": "alfa", "eposta": "izle2@alfa.test", "parola": "Izleyici123!"},
        ),
    )
    r = await kurulu_istemci.post(
        "/api/v1/sozlesmeler",
        json={
            "firma_id": fid,
            "baslik": "X",
            "baslangic_tarihi": "2026-01-01",
            "bitis_tarihi": "2026-02-01",
        },
        headers=izle,
    )
    assert r.status_code == 403, r.text


async def test_sozlesme_tenant_izolasyonu(kurulu_istemci: AsyncClient) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    fid = await _firma(kurulu_istemci, ha, "İzole Sözleşme Firma")
    sa = await _sozlesme(kurulu_istemci, ha, fid)
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    r = await kurulu_istemci.get(f"/api/v1/sozlesmeler/{sa['id']}", headers=hb)
    assert r.status_code == 404, r.text
