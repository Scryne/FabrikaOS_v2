"""S12 entegrasyon: DYS belge + sürüm — yükleme/indirme, sürümleme, izolasyon, RBAC.

Nesne depolama testte ``BellekNesneDepo`` ile değiştirilir (altyapısız).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from httpx import AsyncClient

from app.modules.dys.depolama import BellekNesneDepo, nesne_depo_ayarla
from tests.conftest import ALFA, BETA

KIMLIK = "/api/v1/kimlik"


@pytest.fixture(autouse=True)
def _bellek_depo() -> Iterator[BellekNesneDepo]:
    depo = BellekNesneDepo()
    nesne_depo_ayarla(depo)
    try:
        yield depo
    finally:
        nesne_depo_ayarla(None)


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


async def _belge(istemci: AsyncClient, h: dict[str, str], ad: str = "Kalite El Kitabı") -> dict:
    r = await istemci.post(
        "/api/v1/belgeler", json={"ad": ad, "kategori": "prosedur"}, headers=h
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]


async def test_belge_oto_kod_surumsuz(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    b = await _belge(kurulu_istemci, h)
    assert b["kod"].startswith("BLG-")
    assert b["guncel_surum"] == 0


async def test_surum_yukle_indir(
    kurulu_istemci: AsyncClient, _bellek_depo: BellekNesneDepo
) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    b = await _belge(kurulu_istemci, h)
    icerik = b"PDF-icerik-v1"
    r = await kurulu_istemci.post(
        f"/api/v1/belgeler/{b['id']}/surumler",
        files={"dosya": ("rapor.txt", icerik, "text/plain")},
        data={"aciklama": "ilk sürüm"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    surum = r.json()["data"]
    assert surum["surum_no"] == 1
    assert surum["boyut"] == len(icerik)
    assert "nesne_anahtari" not in surum  # depolama detayı gizli
    # belge guncel_surum arttı
    det = await kurulu_istemci.get(f"/api/v1/belgeler/{b['id']}", headers=h)
    assert det.json()["data"]["guncel_surum"] == 1
    # içerik indirilince aynı
    ind = await kurulu_istemci.get(
        f"/api/v1/belgeler/{b['id']}/surumler/1/indir", headers=h
    )
    assert ind.status_code == 200
    assert ind.content == icerik
    assert ind.headers["content-type"].startswith("text/plain")


async def test_surumleme_artan(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    b = await _belge(kurulu_istemci, h)
    for i, icerik in enumerate((b"v1", b"v2", b"v3"), start=1):
        r = await kurulu_istemci.post(
            f"/api/v1/belgeler/{b['id']}/surumler",
            files={"dosya": (f"d{i}.bin", icerik, "application/octet-stream")},
            headers=h,
        )
        assert r.json()["data"]["surum_no"] == i
    liste = await kurulu_istemci.get(f"/api/v1/belgeler/{b['id']}/surumler", headers=h)
    surumler = liste.json()["data"]
    assert [s["surum_no"] for s in surumler] == [3, 2, 1]  # en yeni önce
    # eski sürüm hâlâ indirilebilir (append-only)
    v1 = await kurulu_istemci.get(f"/api/v1/belgeler/{b['id']}/surumler/1/indir", headers=h)
    assert v1.content == b"v1"


async def test_bos_dosya_422(kurulu_istemci: AsyncClient) -> None:
    h = _h("alfa", await _giris(kurulu_istemci, ALFA))
    b = await _belge(kurulu_istemci, h)
    r = await kurulu_istemci.post(
        f"/api/v1/belgeler/{b['id']}/surumler",
        files={"dosya": ("bos.txt", b"", "text/plain")},
        headers=h,
    )
    assert r.status_code == 422, r.text


async def test_dys_rbac_403(kurulu_istemci: AsyncClient) -> None:
    admin = _h("alfa", await _giris(kurulu_istemci, ALFA))
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izle3@alfa.test", "parola": "Izleyici123!", "roller": ["izleyici"]},
        headers=admin,
    )
    izle = _h(
        "alfa",
        await _giris(
            kurulu_istemci,
            {"slug": "alfa", "eposta": "izle3@alfa.test", "parola": "Izleyici123!"},
        ),
    )
    r = await kurulu_istemci.post("/api/v1/belgeler", json={"ad": "Yetkisiz"}, headers=izle)
    assert r.status_code == 403, r.text
    # okuma serbest
    ok = await kurulu_istemci.get("/api/v1/belgeler", headers=izle)
    assert ok.status_code == 200


async def test_dys_tenant_izolasyonu(
    kurulu_istemci: AsyncClient, _bellek_depo: BellekNesneDepo
) -> None:
    ha = _h("alfa", await _giris(kurulu_istemci, ALFA))
    ba = await _belge(kurulu_istemci, ha, "İzole Belge")
    await kurulu_istemci.post(
        f"/api/v1/belgeler/{ba['id']}/surumler",
        files={"dosya": ("g.txt", b"gizli", "text/plain")},
        headers=ha,
    )
    hb = _h("beta", await _giris(kurulu_istemci, BETA))
    # beta belgeyi göremez / indiremez
    assert (await kurulu_istemci.get(f"/api/v1/belgeler/{ba['id']}", headers=hb)).status_code == 404
    ind = await kurulu_istemci.get(f"/api/v1/belgeler/{ba['id']}/surumler/1/indir", headers=hb)
    assert ind.status_code == 404
