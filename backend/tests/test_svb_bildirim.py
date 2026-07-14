"""S-VB bildirim merkezi testleri — üretici (idempotency + izolasyon) + kişisel uçlar.

Üretici doğrudan servis katmanından koşulur (``tenant_uretici_turu``); uçlar HTTP
üzerinden. Testler kendi outbox olaylarını üretir ve iddiaları o olayların
``giden_olay_id``'sine sabitler (paylaşılan test DB'sinde deterministik).
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.core.olaylar import olay_yayinla
from app.kimlik.models import Kullanici
from app.modules.bildirim.models import Bildirim, BildirimImleci, BildirimTercihi
from app.modules.bildirim.uretici import tenant_uretici_turu
from tests.conftest import ALFA
from tests.test_s16_entitlement import _giris

pytestmark = pytest.mark.asyncio

BILDIRIMLER = "/api/v1/bildirimler"
TERCIHLER = "/api/v1/bildirim-tercihleri"


@pytest_asyncio.fixture
async def sm(test_engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[arg-type]


@pytest_asyncio.fixture
async def oturum(sm: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with sm() as s:
        yield s


async def _kullanici_id(oturum: AsyncSession, slug: str, eposta: str) -> int:
    await search_path_ayarla(oturum, slug)
    kid = (
        await oturum.execute(select(Kullanici.id).where(Kullanici.eposta == eposta))
    ).scalar_one()
    return int(kid)


async def _olay_ekle(
    sm: async_sessionmaker[AsyncSession], slug: str, olay_turu: str, govde: dict
) -> int:
    """Tenant şemasına bir outbox olayı yazar (commit'li); olay id döner."""
    async with sm() as s, s.begin():
        await search_path_ayarla(s, slug)
        olay = await olay_yayinla(s, olay_turu=olay_turu, govde=govde)
        return olay.id


async def _bildirim_sayisi(
    oturum: AsyncSession, slug: str, olay_id: int, kullanici_id: int | None = None
) -> int:
    await search_path_ayarla(oturum, slug)
    kosullar = [Bildirim.giden_olay_id == olay_id]
    if kullanici_id is not None:
        kosullar.append(Bildirim.kullanici_id == kullanici_id)
    sayi = (
        await oturum.execute(select(func.count()).select_from(Bildirim).where(*kosullar))
    ).scalar_one()
    return int(sayi)


async def test_stok_kritik_izin_sahibine_duser_ikinci_tur_dup_uretmez(
    test_db: str, sm: async_sessionmaker[AsyncSession], oturum: AsyncSession
) -> None:
    admin_id = await _kullanici_id(oturum, "alfa", ALFA["eposta"])
    olay_id = await _olay_ekle(
        sm, "alfa", "stok.kritik", {"kaynak_id": 991, "malzeme_kodu": "SVB-STK-1"}
    )

    await tenant_uretici_turu(sm, "alfa")
    assert await _bildirim_sayisi(oturum, "alfa", olay_id, admin_id) == 1

    # İkinci tur: imleç ilerlemiş → yeniden işlenmez.
    await tenant_uretici_turu(sm, "alfa")
    assert await _bildirim_sayisi(oturum, "alfa", olay_id, admin_id) == 1

    # İmleç sıfırlansa bile UNIQUE(kullanici_id, giden_olay_id) çift bildirimi önler.
    async with sm() as s, s.begin():
        await search_path_ayarla(s, "alfa")
        await s.execute(update(BildirimImleci).values(son_islenen_olay_id=0))
    await tenant_uretici_turu(sm, "alfa")
    assert await _bildirim_sayisi(oturum, "alfa", olay_id, admin_id) == 1


async def test_tercih_kapaliyken_bildirim_uretilmez(
    test_db: str, sm: async_sessionmaker[AsyncSession], oturum: AsyncSession
) -> None:
    admin_id = await _kullanici_id(oturum, "alfa", ALFA["eposta"])
    # admin, oee.dustu türünü kapatır.
    async with sm() as s, s.begin():
        await search_path_ayarla(s, "alfa")
        s.add(
            BildirimTercihi(
                kullanici_id=admin_id, olay_turu="oee.dustu", uygulama_ici=False, eposta=False
            )
        )
    olay_id = await _olay_ekle(sm, "alfa", "oee.dustu", {"kaynak_id": 992, "kod": "SVB-OEE-1"})
    await tenant_uretici_turu(sm, "alfa")
    assert await _bildirim_sayisi(oturum, "alfa", olay_id, admin_id) == 0


async def test_rapor_hazir_yalniz_olusturana_gider(
    test_db: str, sm: async_sessionmaker[AsyncSession], oturum: AsyncSession
) -> None:
    admin_id = await _kullanici_id(oturum, "alfa", ALFA["eposta"])
    olay_id = await _olay_ekle(
        sm, "alfa", "rapor.hazir", {"kaynak_id": 5, "olusturan_kullanici_id": admin_id}
    )
    await tenant_uretici_turu(sm, "alfa")
    assert await _bildirim_sayisi(oturum, "alfa", olay_id) == 1  # tek hedef: oluşturan
    assert await _bildirim_sayisi(oturum, "alfa", olay_id, admin_id) == 1


async def test_bildirim_tenant_izolasyonu(
    test_db: str, sm: async_sessionmaker[AsyncSession], oturum: AsyncSession
) -> None:
    """7 kritik test ailesi: A'nın olayı B'nin kullanıcısına asla bildirim üretmez."""
    olay_id = await _olay_ekle(
        sm, "alfa", "stok.kritik", {"kaynak_id": 993, "malzeme_kodu": "SVB-IZO-1"}
    )
    await tenant_uretici_turu(sm, "alfa")
    await tenant_uretici_turu(sm, "beta")

    # Beta şemasında bu olaya (veya alfa kaynaklı herhangi bir işarete) bağlı satır yok.
    await search_path_ayarla(oturum, "beta")
    beta_sayi = (
        await oturum.execute(
            select(func.count())
            .select_from(Bildirim)
            .where(Bildirim.veri["kaynak_id"].astext == "993")
        )
    ).scalar_one()
    assert int(beta_sayi) == 0
    # Alfa'da üretildi (kontrol).
    assert await _bildirim_sayisi(oturum, "alfa", olay_id) >= 1


async def test_ucler_yalniz_kendi_bildirimleri_ve_okundu_akisi(
    test_db: str,
    sm: async_sessionmaker[AsyncSession],
    oturum: AsyncSession,
    kurulu_istemci: AsyncClient,
) -> None:
    alfa_h = await _giris(kurulu_istemci, ALFA)

    # İkinci kullanıcı (rolsüz — kişisel uçlar izin istemez).
    r = await kurulu_istemci.post(
        "/api/v1/kullanicilar",
        json={"eposta": "svb-user2@alfa.test", "parola": "Deneme12345!", "ad_soyad": "SVB İki"},
        headers=alfa_h,
    )
    assert r.status_code == 201, r.text
    user2_h = await _giris(
        kurulu_istemci,
        {"slug": "alfa", "eposta": "svb-user2@alfa.test", "parola": "Deneme12345!"},
    )

    admin_id = await _kullanici_id(oturum, "alfa", ALFA["eposta"])
    # Yalnız admin'e kişi-hedefli bildirim üret.
    await _olay_ekle(
        sm, "alfa", "rapor.hazir", {"kaynak_id": 6, "olusturan_kullanici_id": admin_id}
    )
    await tenant_uretici_turu(sm, "alfa")

    # Admin listesinde görünür.
    r = await kurulu_istemci.get(f"{BILDIRIMLER}?olay_turu=rapor.hazir", headers=alfa_h)
    assert r.status_code == 200
    idler = [b["id"] for b in r.json()["data"]]
    assert idler, "admin bildirimi bekleniyordu"
    bildirim_id = idler[0]

    # user2 listesinde görünmez; başkasının bildirimi okundu yapılamaz (404).
    r = await kurulu_istemci.get(f"{BILDIRIMLER}?olay_turu=rapor.hazir", headers=user2_h)
    assert r.status_code == 200 and r.json()["data"] == []
    r = await kurulu_istemci.post(f"{BILDIRIMLER}/{bildirim_id}/okundu", headers=user2_h)
    assert r.status_code == 404

    # Sahibi okundu işaretler; özet sayacı düşer.
    r = await kurulu_istemci.get(f"{BILDIRIMLER}/ozet", headers=alfa_h)
    okunmamis_once = r.json()["data"]["okunmamis"]
    r = await kurulu_istemci.post(f"{BILDIRIMLER}/{bildirim_id}/okundu", headers=alfa_h)
    assert r.status_code == 200 and r.json()["data"]["okundu"] is True
    r = await kurulu_istemci.get(f"{BILDIRIMLER}/ozet", headers=alfa_h)
    assert r.json()["data"]["okunmamis"] == okunmamis_once - 1

    # Tümünü okundu: okunmamış sıfırlanır.
    r = await kurulu_istemci.post(f"{BILDIRIMLER}/tumunu-okundu", headers=alfa_h)
    assert r.status_code == 200
    r = await kurulu_istemci.get(f"{BILDIRIMLER}/ozet", headers=alfa_h)
    assert r.json()["data"]["okunmamis"] == 0

    # Kimliksiz erişim reddedilir.
    r = await kurulu_istemci.get(BILDIRIMLER, headers={"X-Tenant": "alfa"})
    assert r.status_code == 401


async def test_tercih_ucu_katalog_ve_upsert(test_db: str, kurulu_istemci: AsyncClient) -> None:
    h = await _giris(kurulu_istemci, ALFA)

    r = await kurulu_istemci.get(TERCIHLER, headers=h)
    assert r.status_code == 200
    katalog = {t["olay_turu"]: t for t in r.json()["data"]}
    assert "stok.kritik" in katalog and "sla.asildi" in katalog
    assert katalog["sozlesme.yaklasiyor"]["uygulama_ici"] is True  # varsayılan açık

    # Upsert: kapat → GET yansıtır.
    r = await kurulu_istemci.put(
        TERCIHLER,
        json={
            "tercihler": [
                {"olay_turu": "sozlesme.yaklasiyor", "uygulama_ici": False, "eposta": False}
            ]
        },
        headers=h,
    )
    assert r.status_code == 200, r.text
    r = await kurulu_istemci.get(TERCIHLER, headers=h)
    katalog = {t["olay_turu"]: t for t in r.json()["data"]}
    assert katalog["sozlesme.yaklasiyor"]["uygulama_ici"] is False

    # Katalog dışı olay türü 422.
    r = await kurulu_istemci.put(
        TERCIHLER,
        json={"tercihler": [{"olay_turu": "yok.boyle", "uygulama_ici": True, "eposta": False}]},
        headers=h,
    )
    assert r.status_code == 422


async def test_duyuru_yayini_outbox_uzerinden_herkese_bildirim(
    test_db: str,
    sm: async_sessionmaker[AsyncSession],
    oturum: AsyncSession,
    kurulu_istemci: AsyncClient,
) -> None:
    h = await _giris(kurulu_istemci, ALFA)
    r = await kurulu_istemci.post(
        "/api/v1/duyurular",
        json={"baslik": "SVB duyuru", "icerik": "test", "onem": "bilgi"},
        headers=h,
    )
    assert r.status_code == 201, r.text
    duyuru_id = r.json()["data"]["id"]
    r = await kurulu_istemci.post(f"/api/v1/duyurular/{duyuru_id}/yayinla", headers=h)
    assert r.status_code == 200, r.text

    await tenant_uretici_turu(sm, "alfa")
    await search_path_ayarla(oturum, "alfa")
    sayi = (
        await oturum.execute(
            select(func.count())
            .select_from(Bildirim)
            .where(
                Bildirim.olay_turu == "duyuru.yeni",
                Bildirim.veri["kaynak_id"].astext == str(duyuru_id),
            )
        )
    ).scalar_one()
    # Tüm aktif alfa kullanıcıları (en az admin) bildirim alır.
    assert int(sayi) >= 1
