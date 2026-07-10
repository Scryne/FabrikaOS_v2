"""S17 platform okuma uçları testleri — tenantlar/abonelikler/planlar/saglik."""

from __future__ import annotations

from httpx import AsyncClient

from app.modules.dys.depolama import BellekNesneDepo, nesne_depo_ayarla
from tests.conftest import ALFA
from tests.test_s16_entitlement import _giris
from tests.test_s17_platform_kimlik import (  # noqa: F401  (fixture'lar)
    oturum,
    platform_db,
    platform_giris,
)

TENANTLAR = "/api/v1/platform/tenantlar"


async def test_tenant_listesi_plan_ve_koltuk_bilgisiyle(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    r = await kurulu_istemci.get(TENANTLAR, headers=h)
    assert r.status_code == 200, r.text
    govde = r.json()
    assert govde["meta"]["toplam"] >= 2
    satirlar = {s["slug"]: s for s in govde["data"]}
    assert "alfa" in satirlar and "beta" in satirlar
    alfa = satirlar["alfa"]
    assert alfa["plan_kodu"] == "kurumsal"
    assert alfa["abonelik_durum"] == "deneme"
    assert alfa["aktif"] is True
    assert alfa["koltuk_limiti"] is None  # kurumsal = sınırsız
    assert alfa["koltuk_kullanilan"] >= 1  # en az provizyon admini


async def test_tenant_listesi_arama_filtreler(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    r = await kurulu_istemci.get(TENANTLAR, params={"arama": "alfa"}, headers=h)
    assert r.status_code == 200
    sluglar = [s["slug"] for s in r.json()["data"]]
    assert "alfa" in sluglar and "beta" not in sluglar


async def test_tenant_detayi_matris_ve_koltuk(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    liste = (await kurulu_istemci.get(TENANTLAR, params={"arama": "alfa"}, headers=h)).json()
    alfa_id = liste["data"][0]["id"]

    r = await kurulu_istemci.get(f"{TENANTLAR}/{alfa_id}", headers=h)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["slug"] == "alfa"
    assert veri["plan_kodu"] == "kurumsal"
    assert len(veri["moduller"]) == 17
    assert all(m["kaynak"] == "plan" for m in veri["moduller"])  # override yok
    assert len(veri["ozellikler"]) == 2
    assert veri["koltuk_kullanilan"] >= 1


async def test_tenant_detayi_bulunamadi_404(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    r = await kurulu_istemci.get(f"{TENANTLAR}/999999", headers=h)
    assert r.status_code == 404


async def test_abonelik_listesi(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    r = await kurulu_istemci.get("/api/v1/platform/abonelikler", headers=h)
    assert r.status_code == 200, r.text
    sluglar = {s["tenant_slug"] for s in r.json()["data"]}
    assert {"alfa", "beta"} <= sluglar


async def test_plan_katalogu(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    r = await kurulu_istemci.get("/api/v1/platform/planlar", headers=h)
    assert r.status_code == 200, r.text
    kodlar = {p["kod"] for p in r.json()["data"]}
    assert kodlar == {"deneme", "temel", "profesyonel", "kurumsal"}


async def test_saglik_sondalari(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    nesne_depo_ayarla(BellekNesneDepo())
    try:
        r = await kurulu_istemci.get("/api/v1/platform/saglik", headers=h)
    finally:
        nesne_depo_ayarla(None)
    assert r.status_code == 200, r.text
    veri = r.json()["data"]
    assert veri["veritabani"]["durum"] == "saglikli"
    assert veri["redis"]["durum"] == "saglikli"  # fakeredis ping
    assert veri["nesne_depo"]["durum"] == "saglikli"  # bellek deposu
    assert veri["tenant_toplam"] >= 2
    assert veri["tenant_askida"] == veri["tenant_toplam"] - veri["tenant_aktif"]


async def test_okuma_uclari_tenant_tokenina_kapali(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    tenant_h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.get(TENANTLAR, headers={"Authorization": tenant_h["Authorization"]})
    assert r.status_code == 401
