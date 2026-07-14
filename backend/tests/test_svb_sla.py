"""S-VB SLA taraması testleri — kenar-tetikli ``sla.asildi`` (bir-kez) + RBAC/izolasyon."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.core.olaylar import GidenOlay
from tests.conftest import ALFA, BETA
from tests.test_s16_entitlement import _giris

pytestmark = pytest.mark.asyncio

IS_EMIRLERI = "/api/v1/is-emirleri"
TALEPLER = "/api/v1/talepler"


@pytest_asyncio.fixture
async def oturum(test_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[arg-type]
    async with sm() as s:
        yield s


async def _sla_olay_sayisi(oturum: AsyncSession, slug: str, kaynak_tur: str, kaynak_id: int) -> int:
    await search_path_ayarla(oturum, slug)
    sayi = (
        await oturum.execute(
            select(func.count())
            .select_from(GidenOlay)
            .where(
                GidenOlay.olay_turu == "sla.asildi",
                GidenOlay.govde["kaynak_tur"].astext == kaynak_tur,
                GidenOlay.govde["kaynak_id"].astext == str(kaynak_id),
            )
        )
    ).scalar_one()
    return int(sayi)


async def _makine_olustur(istemci: AsyncClient, h: dict[str, str], kod: str) -> int:
    r = await istemci.post(
        "/api/v1/makineler", json={"kod": kod, "ad": f"{kod} makinesi"}, headers=h
    )
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


async def test_is_emri_sla_asimi_bir_kez_bildirilir(
    test_db: str, kurulu_istemci: AsyncClient, oturum: AsyncSession
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _makine_olustur(kurulu_istemci, h, "SVB-SLA-1")
    gecmis = (datetime.now(UTC) - timedelta(hours=3)).isoformat()

    # Hedefi geçmiş açık iş emri.
    r = await kurulu_istemci.post(
        IS_EMIRLERI,
        json={"baslik": "SLA gecikmiş", "makine_id": mid, "hedef_tarih": gecmis},
        headers=h,
    )
    assert r.status_code == 201, r.text
    gecikmis_id = r.json()["data"]["id"]
    assert r.json()["data"]["hedef_tarih"] is not None

    # Hedefi gelecekte olan iş emri (olay ÜRETMEMELİ).
    gelecek = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    r = await kurulu_istemci.post(
        IS_EMIRLERI,
        json={"baslik": "SLA vadeli", "makine_id": mid, "hedef_tarih": gelecek},
        headers=h,
    )
    vadeli_id = r.json()["data"]["id"]

    # İlk tarama: yalnız gecikmiş kayıt için tek olay.
    r = await kurulu_istemci.post(f"{IS_EMIRLERI}/sla-tara", headers=h)
    assert r.status_code == 200, r.text
    assert await _sla_olay_sayisi(oturum, "alfa", "is_emri", gecikmis_id) == 1
    assert await _sla_olay_sayisi(oturum, "alfa", "is_emri", vadeli_id) == 0

    # İkinci tarama: dedup — aday hâlâ açık ama yeni olay yazılmaz.
    r = await kurulu_istemci.post(f"{IS_EMIRLERI}/sla-tara", headers=h)
    assert r.status_code == 200
    assert r.json()["data"]["islenen"] == 0
    assert await _sla_olay_sayisi(oturum, "alfa", "is_emri", gecikmis_id) == 1


async def test_terminal_is_emri_sla_olayi_uretmez(
    test_db: str, kurulu_istemci: AsyncClient, oturum: AsyncSession
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    mid = await _makine_olustur(kurulu_istemci, h, "SVB-SLA-2")
    gecmis = (datetime.now(UTC) - timedelta(hours=5)).isoformat()
    r = await kurulu_istemci.post(
        IS_EMIRLERI,
        json={"baslik": "SLA iptal", "makine_id": mid, "hedef_tarih": gecmis},
        headers=h,
    )
    ie_id = r.json()["data"]["id"]
    r = await kurulu_istemci.patch(
        f"{IS_EMIRLERI}/{ie_id}/durum", json={"durum": "iptal"}, headers=h
    )
    assert r.status_code == 200, r.text

    await kurulu_istemci.post(f"{IS_EMIRLERI}/sla-tara", headers=h)
    assert await _sla_olay_sayisi(oturum, "alfa", "is_emri", ie_id) == 0


async def test_talep_sla_asimi_ve_cozulmus_haric(
    test_db: str, kurulu_istemci: AsyncClient, oturum: AsyncSession
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    gecmis = (datetime.now(UTC) - timedelta(hours=1)).isoformat()

    r = await kurulu_istemci.post(
        TALEPLER, json={"baslik": "SLA talep", "hedef_tarih": gecmis}, headers=h
    )
    assert r.status_code == 201, r.text
    gecikmis_id = r.json()["data"]["id"]

    # Çözülmüş talep SLA olayı üretmez.
    r = await kurulu_istemci.post(
        TALEPLER, json={"baslik": "SLA çözülmüş", "hedef_tarih": gecmis}, headers=h
    )
    cozulmus_id = r.json()["data"]["id"]
    await kurulu_istemci.patch(
        f"{TALEPLER}/{cozulmus_id}/durum", json={"durum": "inceleniyor"}, headers=h
    )
    await kurulu_istemci.patch(
        f"{TALEPLER}/{cozulmus_id}/durum", json={"durum": "cozuldu"}, headers=h
    )

    r = await kurulu_istemci.post(f"{TALEPLER}/sla-tara", headers=h)
    assert r.status_code == 200, r.text
    assert await _sla_olay_sayisi(oturum, "alfa", "talep", gecikmis_id) == 1
    assert await _sla_olay_sayisi(oturum, "alfa", "talep", cozulmus_id) == 0

    # Dedup: ikinci tarama ikinci olay üretmez.
    await kurulu_istemci.post(f"{TALEPLER}/sla-tara", headers=h)
    assert await _sla_olay_sayisi(oturum, "alfa", "talep", gecikmis_id) == 1


async def test_sla_tara_rbac_ve_izolasyon(
    test_db: str, kurulu_istemci: AsyncClient, oturum: AsyncSession
) -> None:
    # Yetkisiz (rolsüz) kullanıcı 403.
    alfa_h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "svb-sla@alfa.test", "parola": "Deneme12345!", "ad_soyad": "SLA Test"},
        headers=alfa_h,
    )
    assert r.status_code == 201, r.text
    rolsuz_h = await _giris(
        kurulu_istemci,
        {"slug": "alfa", "eposta": "svb-sla@alfa.test", "parola": "Deneme12345!"},
    )
    r = await kurulu_istemci.post(f"{IS_EMIRLERI}/sla-tara", headers=rolsuz_h)
    assert r.status_code == 403

    # İzolasyon: alfa'daki gecikmiş kayıt, beta taramasında olay üretmez.
    mid = await _makine_olustur(kurulu_istemci, alfa_h, "SVB-SLA-3")
    gecmis = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
    r = await kurulu_istemci.post(
        IS_EMIRLERI,
        json={"baslik": "İzolasyon SLA", "makine_id": mid, "hedef_tarih": gecmis},
        headers=alfa_h,
    )
    ie_id = r.json()["data"]["id"]

    beta_h = await _giris(kurulu_istemci, BETA)
    r = await kurulu_istemci.post(f"{IS_EMIRLERI}/sla-tara", headers=beta_h)
    assert r.status_code == 200
    assert await _sla_olay_sayisi(oturum, "beta", "is_emri", ie_id) == 0
