"""S17 entitlement yazma API testleri — S16'nın ertelediği yüzey.

Kabul: PUT modül kapat → tenant'ın bir SONRAKİ isteği 403 ``MODUL_KAPALI``;
``acik: null`` → override kalkar, plana döner; katalog dışı kod 422.
"""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.control_plane.models import PlatformDenetimIzi
from tests.conftest import ALFA
from tests.test_s16_entitlement import _giris
from tests.test_s17_platform_kimlik import (  # noqa: F401  (fixture'lar)
    oturum,
    platform_db,
    platform_giris,
)

TENANTLAR = "/api/v1/platform/tenantlar"


async def _alfa_id(istemci: AsyncClient, h: dict[str, str]) -> int:
    r = await istemci.get(TENANTLAR, params={"arama": "alfa"}, headers=h)
    return int(r.json()["data"][0]["id"])


async def test_modul_kapat_aninda_403_null_plana_doner(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    alfa_id = await _alfa_id(kurulu_istemci, h)
    tenant_h = await _giris(kurulu_istemci, ALFA)

    # kurumsal planda ai açık.
    r = await kurulu_istemci.get("/api/v1/tahmin/modeller", headers=tenant_h)
    assert r.status_code == 200, r.text

    try:
        # Platformdan kapat → matris yanıtında kaynak "hak".
        r = await kurulu_istemci.put(
            f"{TENANTLAR}/{alfa_id}/modul-haklari/ai", json={"acik": False}, headers=h
        )
        assert r.status_code == 200, r.text
        durum = {m["kod"]: m for m in r.json()["data"]}
        assert durum["ai"]["acik"] is False
        assert durum["ai"]["kaynak"] == "hak"

        # Tenant'ın bir SONRAKİ isteği 403 (önbellek yok).
        r = await kurulu_istemci.get("/api/v1/tahmin/modeller", headers=tenant_h)
        assert r.status_code == 403
        assert r.json()["hata_kodu"] == "MODUL_KAPALI"
    finally:
        # null → override kalkar (testler arası durumu geri yükle).
        r = await kurulu_istemci.put(
            f"{TENANTLAR}/{alfa_id}/modul-haklari/ai", json={"acik": None}, headers=h
        )
        assert r.status_code == 200, r.text

    durum = {m["kod"]: m for m in r.json()["data"]}
    assert durum["ai"]["acik"] is True
    assert durum["ai"]["kaynak"] == "plan"
    r = await kurulu_istemci.get("/api/v1/tahmin/modeller", headers=tenant_h)
    assert r.status_code == 200


async def test_ozellik_bayragi_yaz_ve_tenant_gorunumu(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    alfa_id = await _alfa_id(kurulu_istemci, h)
    tenant_h = await _giris(kurulu_istemci, ALFA)

    try:
        r = await kurulu_istemci.put(
            f"{TENANTLAR}/{alfa_id}/ozellik-bayraklari/mobil-api",
            json={"acik": False},
            headers=h,
        )
        assert r.status_code == 200, r.text
        durum = {o["kod"]: o for o in r.json()["data"]}
        assert durum["mobil-api"]["acik"] is False
        assert durum["mobil-api"]["kaynak"] == "bayrak"

        # Tenant tarafındaki /moduller görünümü de anında değişir.
        r = await kurulu_istemci.get("/api/v1/moduller", headers=tenant_h)
        ozellik = {o["kod"]: o for o in r.json()["data"]["ozellikler"]}
        assert ozellik["mobil-api"]["acik"] is False
    finally:
        r = await kurulu_istemci.put(
            f"{TENANTLAR}/{alfa_id}/ozellik-bayraklari/mobil-api",
            json={"acik": None},
            headers=h,
        )
        assert r.status_code == 200


async def test_katalog_disi_kodlar_422(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
) -> None:
    h = await platform_giris(kurulu_istemci)
    alfa_id = await _alfa_id(kurulu_istemci, h)
    r = await kurulu_istemci.put(
        f"{TENANTLAR}/{alfa_id}/modul-haklari/olmayan-modul", json={"acik": True}, headers=h
    )
    assert r.status_code == 422
    r = await kurulu_istemci.put(
        f"{TENANTLAR}/{alfa_id}/ozellik-bayraklari/olmayan-ozellik",
        json={"acik": True},
        headers=h,
    )
    assert r.status_code == 422


async def test_entitlement_yazmalari_denetim_izinde(
    platform_db: None,  # noqa: F811
    kurulu_istemci: AsyncClient,
    oturum: AsyncSession,  # noqa: F811
) -> None:
    h = await platform_giris(kurulu_istemci)
    alfa_id = await _alfa_id(kurulu_istemci, h)
    await kurulu_istemci.put(
        f"{TENANTLAR}/{alfa_id}/modul-haklari/dys", json={"acik": True}, headers=h
    )
    await kurulu_istemci.put(
        f"{TENANTLAR}/{alfa_id}/modul-haklari/dys", json={"acik": None}, headers=h
    )
    eylemler = (
        (
            await oturum.execute(
                select(PlatformDenetimIzi.eylem).where(
                    PlatformDenetimIzi.kaynak == "tenant",
                    PlatformDenetimIzi.kaynak_id == str(alfa_id),
                )
            )
        )
        .scalars()
        .all()
    )
    assert "modul_hakki" in eylemler
