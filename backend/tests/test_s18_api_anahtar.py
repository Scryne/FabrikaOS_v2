"""S18 API anahtarı testleri — yaşam döngüsü, özet saklama, kapsam, 401/403, izolasyon."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.tenancy import search_path_ayarla
from app.modules.entegrasyon.models import ApiAnahtari
from app.modules.entegrasyon.service import anahtar_ozetle
from tests.conftest import ALFA
from tests.test_s16_entitlement import GAMMA, _giris, gamma_db, oturum  # noqa: F401

ANAHTARLAR = "/api/v1/api-anahtarlari"
DISVERI = "/api/v1/entegrasyon"


@pytest_asyncio.fixture
async def alfa_h(kurulu_istemci: AsyncClient) -> dict[str, str]:
    return await _giris(kurulu_istemci, ALFA)


async def _anahtar_olustur(
    kurulu_istemci: AsyncClient, h: dict[str, str], **degisiklik: object
) -> tuple[int, str]:
    govde = {"ad": "ERP anahtarı", "izinler": ["stok:oku", "satinalma:oku"], **degisiklik}
    r = await kurulu_istemci.post(ANAHTARLAR, json=govde, headers=h)
    assert r.status_code == 201, r.text
    veri = r.json()["data"]
    return veri["id"], veri["anahtar"]


def _dis_h(anahtar: str, slug: str = "alfa") -> dict[str, str]:
    # Dış yüzeyde JWT YOK — yalnız tenant + API anahtarı.
    return {"X-Tenant": slug, "X-API-Anahtar": anahtar}


async def test_olustur_bir_kez_liste_onek_ozet_saklama(
    kurulu_istemci: AsyncClient,
    alfa_h: dict[str, str],
    oturum: AsyncSession,  # noqa: F811
) -> None:
    aid, duz = await _anahtar_olustur(kurulu_istemci, alfa_h)
    assert duz.startswith("fos_") and len(duz) > 30

    r = await kurulu_istemci.get(ANAHTARLAR, headers=alfa_h)
    satir = next(a for a in r.json()["data"] if a["id"] == aid)
    assert satir["anahtar"] is None  # düz anahtar bir daha asla dönmez
    assert satir["onek"] == duz[:12]

    # DB'de düz anahtar YOK — yalnız SHA-256 özet.
    await search_path_ayarla(oturum, "alfa")
    kayit = (await oturum.execute(select(ApiAnahtari).where(ApiAnahtari.id == aid))).scalar_one()
    assert kayit.anahtar_ozet == anahtar_ozetle(duz)
    assert duz not in (kayit.ad, kayit.onek, kayit.anahtar_ozet)


async def test_kapsam_disi_izin_422(kurulu_istemci: AsyncClient, alfa_h: dict[str, str]) -> None:
    r = await kurulu_istemci.post(
        ANAHTARLAR, json={"ad": "kötü", "izinler": ["kullanici:yaz"]}, headers=alfa_h
    )
    assert r.status_code == 422, r.text
    assert "kullanici:yaz" in r.text


async def test_anahtar_ile_stok_bakiyeleri(
    kurulu_istemci: AsyncClient, alfa_h: dict[str, str]
) -> None:
    await kurulu_istemci.post(
        "/api/v1/malzemeler",
        json={"kod": "ENT-M1", "ad": "Entegrasyon Malzemesi", "birim": "adet"},
        headers=alfa_h,
    )
    _, duz = await _anahtar_olustur(kurulu_istemci, alfa_h)

    r = await kurulu_istemci.get(f"{DISVERI}/stok-bakiyeleri", headers=_dis_h(duz))
    assert r.status_code == 200, r.text
    kodlar = {m["kod"] for m in r.json()["data"]}
    assert "ENT-M1" in kodlar


async def test_kapsam_yetersiz_403(kurulu_istemci: AsyncClient, alfa_h: dict[str, str]) -> None:
    _, duz = await _anahtar_olustur(kurulu_istemci, alfa_h, izinler=["stok:oku"])
    r = await kurulu_istemci.get(f"{DISVERI}/uretim-ozeti", headers=_dis_h(duz))
    assert r.status_code == 403, r.text  # geçerli anahtar, eksik kapsam


async def test_eksik_yanlis_pasif_suresi_dolmus_401(
    kurulu_istemci: AsyncClient, alfa_h: dict[str, str]
) -> None:
    r = await kurulu_istemci.get(f"{DISVERI}/stok-bakiyeleri", headers={"X-Tenant": "alfa"})
    assert r.status_code == 401  # başlık yok

    r = await kurulu_istemci.get(
        f"{DISVERI}/stok-bakiyeleri", headers=_dis_h("fos_boyle-bir-anahtar-yok")
    )
    assert r.status_code == 401  # bilinmeyen anahtar

    aid, duz = await _anahtar_olustur(kurulu_istemci, alfa_h)
    r = await kurulu_istemci.patch(f"{ANAHTARLAR}/{aid}", json={"aktif": False}, headers=alfa_h)
    assert r.status_code == 200
    r = await kurulu_istemci.get(f"{DISVERI}/stok-bakiyeleri", headers=_dis_h(duz))
    assert r.status_code == 401  # pasif anahtar — var/yok ayrımı sızdırılmaz

    _, dolmus = await _anahtar_olustur(
        kurulu_istemci,
        alfa_h,
        gecerlilik_tarihi=(datetime.now(UTC) - timedelta(days=1)).isoformat(),
    )
    r = await kurulu_istemci.get(f"{DISVERI}/stok-bakiyeleri", headers=_dis_h(dolmus))
    assert r.status_code == 401  # süresi dolmuş


async def test_silinen_anahtar_aninda_gecersiz(
    kurulu_istemci: AsyncClient, alfa_h: dict[str, str]
) -> None:
    aid, duz = await _anahtar_olustur(kurulu_istemci, alfa_h)
    r = await kurulu_istemci.get(f"{DISVERI}/stok-bakiyeleri", headers=_dis_h(duz))
    assert r.status_code == 200
    r = await kurulu_istemci.delete(f"{ANAHTARLAR}/{aid}", headers=alfa_h)
    assert r.status_code == 200
    r = await kurulu_istemci.get(f"{DISVERI}/stok-bakiyeleri", headers=_dis_h(duz))
    assert r.status_code == 401


async def test_anahtar_tenant_izole(kurulu_istemci: AsyncClient, alfa_h: dict[str, str]) -> None:
    _, duz = await _anahtar_olustur(kurulu_istemci, alfa_h)
    # Alfa'nın anahtarı beta bağlamında YOKTUR (şema-izole arama) → 401.
    r = await kurulu_istemci.get(f"{DISVERI}/stok-bakiyeleri", headers=_dis_h(duz, slug="beta"))
    assert r.status_code == 401


async def test_satinalma_talepleri_ve_uretim_ozeti(
    kurulu_istemci: AsyncClient, alfa_h: dict[str, str]
) -> None:
    # Satınalma talebi (taslak) + üretim verisi hazırla.
    r = await kurulu_istemci.post(
        "/api/v1/malzemeler",
        json={"kod": "ENT-M2", "ad": "Talep Malzemesi", "birim": "kg"},
        headers=alfa_h,
    )
    malzeme_id = r.json()["data"]["id"]
    r = await kurulu_istemci.post(
        "/api/v1/satinalma-talepleri",
        json={
            "baslik": "ERP senkron talebi",
            "kalemler": [{"malzeme_id": malzeme_id, "miktar": 5, "birim": "kg"}],
        },
        headers=alfa_h,
    )
    assert r.status_code == 201, r.text

    r = await kurulu_istemci.post(
        "/api/v1/makineler", json={"kod": "ENT-MAK", "ad": "Entegrasyon Presi"}, headers=alfa_h
    )
    makine_id = r.json()["data"]["id"]
    r = await kurulu_istemci.post(
        "/api/v1/uretim-verileri",
        json={
            "makine_id": makine_id,
            "planlanan_sure_dk": 60,
            "durus_sure_dk": 6,
            "toplam_adet": 100,
            "saglam_adet": 95,
            "ideal_cevrim_sn": 30,
        },
        headers=alfa_h,
    )
    assert r.status_code == 201, r.text

    _, duz = await _anahtar_olustur(kurulu_istemci, alfa_h, izinler=["satinalma:oku", "uretim:oku"])

    r = await kurulu_istemci.get(
        f"{DISVERI}/satinalma-talepleri", params={"durum": "taslak"}, headers=_dis_h(duz)
    )
    assert r.status_code == 200, r.text
    talep = next(t for t in r.json()["data"] if t["baslik"] == "ERP senkron talebi")
    assert talep["kalemler"][0]["miktar"] == 5.0

    r = await kurulu_istemci.get(f"{DISVERI}/uretim-ozeti", headers=_dis_h(duz))
    assert r.status_code == 200, r.text
    satir = next(s for s in r.json()["data"] if s["makine_kod"] == "ENT-MAK")
    assert satir["toplam_adet"] == 100
    assert satir["fire_adet"] == 5
    assert 0 < satir["oee"] <= 1


async def test_temel_planda_modul_kapali(
    gamma_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await _giris(kurulu_istemci, GAMMA)
    r = await kurulu_istemci.get(ANAHTARLAR, headers=h)
    assert r.status_code == 403, r.text
    assert r.json()["hata_kodu"] == "MODUL_KAPALI"  # bayrak webhook'a özel; burada geçmez
