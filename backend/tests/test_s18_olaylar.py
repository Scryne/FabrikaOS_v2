"""S18 yeni domain olayları — kenar-tetikli `ariza.olustu` + `oee.dustu` (dedup'lu)."""

from __future__ import annotations

import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.tenancy import search_path_ayarla
from app.core.olaylar import GidenOlay
from tests.conftest import ALFA
from tests.test_s16_entitlement import _giris, oturum  # noqa: F401

MAKINELER = "/api/v1/makineler"


@pytest_asyncio.fixture
async def alfa_h(kurulu_istemci: AsyncClient) -> dict[str, str]:
    return await _giris(kurulu_istemci, ALFA)


async def _olay_sayisi(db: AsyncSession, olay_turu: str, makine_id: int) -> int:
    await search_path_ayarla(db, "alfa")
    sayi = (
        await db.execute(
            select(func.count())
            .select_from(GidenOlay)
            .where(
                GidenOlay.olay_turu == olay_turu,
                GidenOlay.govde["makine_id"].astext == str(makine_id),
            )
        )
    ).scalar_one()
    return int(sayi)


async def _makine_olustur(
    kurulu_istemci: AsyncClient, h: dict[str, str], kod: str, **ekstra: object
) -> int:
    r = await kurulu_istemci.post(
        MAKINELER, json={"kod": kod, "ad": f"{kod} makinesi", **ekstra}, headers=h
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


async def test_ariza_olustu_kenar_tetikli(
    kurulu_istemci: AsyncClient,
    alfa_h: dict[str, str],
    oturum: AsyncSession,  # noqa: F811
) -> None:
    mid = await _makine_olustur(kurulu_istemci, alfa_h, "S18-ARZ")

    # durdu → ariza: olay üretilir (aynı transaction'da outbox'a düşer).
    r = await kurulu_istemci.patch(
        f"{MAKINELER}/{mid}/durum", json={"durum": "ariza"}, headers=alfa_h
    )
    assert r.status_code == 200, r.text
    assert await _olay_sayisi(oturum, "ariza.olustu", mid) == 1

    # ariza → ariza: GEÇİŞ YOK → ikinci olay üretilmez (kenar-tetik).
    await kurulu_istemci.patch(f"{MAKINELER}/{mid}/durum", json={"durum": "ariza"}, headers=alfa_h)
    assert await _olay_sayisi(oturum, "ariza.olustu", mid) == 1

    # ariza → calisiyor → ariza: yeni kenar → ikinci olay.
    await kurulu_istemci.patch(
        f"{MAKINELER}/{mid}/durum", json={"durum": "calisiyor"}, headers=alfa_h
    )
    await kurulu_istemci.patch(f"{MAKINELER}/{mid}/durum", json={"durum": "ariza"}, headers=alfa_h)
    assert await _olay_sayisi(oturum, "ariza.olustu", mid) == 2

    # Gövde webhook zarfına yetecek bağlamı taşır.
    await search_path_ayarla(oturum, "alfa")
    olay = (
        (
            await oturum.execute(
                select(GidenOlay)
                .where(
                    GidenOlay.olay_turu == "ariza.olustu",
                    GidenOlay.govde["makine_id"].astext == str(mid),
                )
                .order_by(GidenOlay.id.desc())
            )
        )
        .scalars()
        .first()
    )
    assert olay is not None
    assert olay.govde["makine_kod"] == "S18-ARZ"
    assert olay.govde["onceki_durum"] == "calisiyor"


async def _uretim_gir(
    kurulu_istemci: AsyncClient, h: dict[str, str], makine_id: int, *, saglam: int
) -> None:
    r = await kurulu_istemci.post(
        "/api/v1/uretim-verileri",
        json={
            "makine_id": makine_id,
            "planlanan_sure_dk": 60,
            "durus_sure_dk": 0,
            "toplam_adet": 100,
            "saglam_adet": saglam,
            "ideal_cevrim_sn": 36,  # ideal süre = 60 dk → performans 1.0
        },
        headers=h,
    )
    assert r.status_code == 201, r.text


async def test_oee_dustu_esik_ve_dedup(
    kurulu_istemci: AsyncClient,
    alfa_h: dict[str, str],
    oturum: AsyncSession,  # noqa: F811
) -> None:
    dusuk = await _makine_olustur(kurulu_istemci, alfa_h, "S18-OEE-DUSUK")
    yuksek = await _makine_olustur(kurulu_istemci, alfa_h, "S18-OEE-YUKSEK")
    await _uretim_gir(kurulu_istemci, alfa_h, dusuk, saglam=40)  # kalite 0.40 → OEE ~0.40
    await _uretim_gir(kurulu_istemci, alfa_h, yuksek, saglam=98)  # OEE ~0.98

    r = await kurulu_istemci.post("/api/v1/oee/dusuk-tara", params={"esik": 0.6}, headers=alfa_h)
    assert r.status_code == 200, r.text
    assert r.json()["data"]["islenen"] >= 1
    assert await _olay_sayisi(oturum, "oee.dustu", dusuk) == 1
    assert await _olay_sayisi(oturum, "oee.dustu", yuksek) == 0  # eşik üstü

    # Aynı gün ikinci tarama: makine+gün dedup → yeni olay YOK.
    r = await kurulu_istemci.post("/api/v1/oee/dusuk-tara", params={"esik": 0.6}, headers=alfa_h)
    assert r.status_code == 200
    assert await _olay_sayisi(oturum, "oee.dustu", dusuk) == 1

    # Gövde: oee < esik ve tarih ISO.
    await search_path_ayarla(oturum, "alfa")
    olay = (
        await oturum.execute(
            select(GidenOlay).where(
                GidenOlay.olay_turu == "oee.dustu",
                GidenOlay.govde["makine_id"].astext == str(dusuk),
            )
        )
    ).scalar_one()
    assert olay.govde["oee"] < olay.govde["esik"] == 0.6
    assert olay.govde["makine_kod"] == "S18-OEE-DUSUK"


async def test_oee_dustu_makine_hedefi_esigi_ezer(
    kurulu_istemci: AsyncClient,
    alfa_h: dict[str, str],
    oturum: AsyncSession,  # noqa: F811
) -> None:
    # Hedefi 0.99 olan makine, %98 OEE ile bile "düşük" sayılır (parametre 0.01 olsa da).
    hedefli = await _makine_olustur(kurulu_istemci, alfa_h, "S18-OEE-HEDEF", oee_hedefi=0.99)
    await _uretim_gir(kurulu_istemci, alfa_h, hedefli, saglam=98)

    r = await kurulu_istemci.post("/api/v1/oee/dusuk-tara", params={"esik": 0.01}, headers=alfa_h)
    assert r.status_code == 200, r.text
    assert await _olay_sayisi(oturum, "oee.dustu", hedefli) == 1


async def test_dusuk_tara_rbac(kurulu_istemci: AsyncClient, alfa_h: dict[str, str]) -> None:
    await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "izleyici18b@alfa.test", "parola": "Izleyici18!", "roller": ["izleyici"]},
        headers=alfa_h,
    )
    izleyici = await _giris(
        kurulu_istemci,
        {"slug": "alfa", "eposta": "izleyici18b@alfa.test", "parola": "Izleyici18!"},
    )
    r = await kurulu_istemci.post("/api/v1/oee/dusuk-tara", headers=izleyici)
    assert r.status_code == 403  # uretim:yaz gerekir
