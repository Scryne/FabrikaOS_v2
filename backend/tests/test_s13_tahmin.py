"""S13 çıkarım servisi entegrasyon testleri — 4 tür + tahmin geçmişi + anomali.tespit outbox."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import fakeredis.aioredis
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.core.exceptions import KaynakBulunamadi
from app.core.olaylar import GidenOlay
from app.core.security import redis_istemci
from app.modules.ai import artefakt, repository, service
from app.modules.dys.depolama import nesne_depo_ayarla
from app.modules.uretim.models import Makine, UretimVerisi
from tests import test_s13_egitim as egitim_yardimci

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def ai_ortam(
    test_engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    sm = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    service.oturum_fabrikasi_ayarla(sm)
    service.es_zamanli_ayarla(True)
    nesne_depo_ayarla(egitim_yardimci._DEPO)
    redis_istemci.redis_ayarla(fakeredis.aioredis.FakeRedis(decode_responses=True))
    yield sm
    service.oturum_fabrikasi_ayarla(None)
    service.es_zamanli_ayarla(False)
    nesne_depo_ayarla(None)
    artefakt.onbellek_temizle()
    redis_istemci.redis_ayarla(None)


async def _egitilmis(sm: async_sessionmaker[AsyncSession], slug: str, tur: str) -> None:
    """Slug'da tur için hazır model garanti eder (yoksa eğitir)."""
    async with sm() as db:
        await search_path_ayarla(db, slug)
        if await repository.aktif_kayit(db, tur) is not None:
            return
        kayit = await service.egitim_baslat(db, tur=tur, kullanici_id=None)
        await db.commit()
        kayit_id = kayit.id
    await service.egitim_calistir(kayit_id, slug, tur)


async def _tahmin(
    sm: async_sessionmaker[AsyncSession], slug: str, tur: str
) -> service.CikarimSonucu:
    async with sm() as db:
        await search_path_ayarla(db, slug)
        sonuc = await service.tahmin_calistir(db, slug=slug, tur=tur, kullanici_id=None)
        await db.commit()
        return sonuc


async def test_aktif_model_yokken_404(
    ai_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    async with ai_ortam() as db:
        await search_path_ayarla(db, "beta")
        with pytest.raises(KaynakBulunamadi):
            await service.tahmin_calistir(
                db, slug="beta", tur="kestirimci_bakim", kullanici_id=None
            )


async def test_oee_tahmini_ufuk_ve_gecmis(
    ai_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    await egitim_yardimci._alfa_seed(ai_ortam)
    await _egitilmis(ai_ortam, "alfa", "oee")
    cikarim = await _tahmin(ai_ortam, "alfa", "oee")
    assert len(cikarim.sonuclar) >= 2  # iki AI test makinesi
    assert any(m["makine_kod"] == "AI-MAK-1" for m in cikarim.sonuclar)  # insan-okur kod
    for makine in cikarim.sonuclar:
        assert len(makine["tahminler"]) == service.OEE_UFUK
        for nokta in makine["tahminler"]:
            assert 0.0 <= nokta["oee"] <= 1.0
    # geçmiş satırı kalıcı ve çıktıyla eşleşir
    async with ai_ortam() as db:
        await search_path_ayarla(db, "alfa")
        kayitlar, toplam = await repository.tahmin_listele(db, tur="oee")
    assert toplam >= 1
    assert kayitlar[0].cikti == cikarim.sonuclar


async def test_kestirimci_bakim_tahmini_risk_alanlari(
    ai_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    await egitim_yardimci._alfa_seed(ai_ortam)
    await _egitilmis(ai_ortam, "alfa", "kestirimci_bakim")
    cikarim = await _tahmin(ai_ortam, "alfa", "kestirimci_bakim")
    assert len(cikarim.sonuclar) >= 2
    for t in cikarim.sonuclar:
        assert 0.0 <= t["risk_skoru"] <= 1.0
        assert t["seviye"] in {"dusuk", "orta", "yuksek"}


async def test_stok_tahmini_kalan_gun(
    ai_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    await egitim_yardimci._alfa_seed(ai_ortam)
    await _egitilmis(ai_ortam, "alfa", "stok")
    cikarim = await _tahmin(ai_ortam, "alfa", "stok")
    m = next(t for t in cikarim.sonuclar if t["kod"] == "AI-MLZ-1")
    # mevcut 120, günlük ~10 → ~12 gün
    assert abs(m["kalan_gun"] - 12.0) < 2.5
    assert m["gunluk_tuketim"] > 0


async def test_anomali_tespiti_outbox_olayi_uretir(
    ai_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    await egitim_yardimci._alfa_seed(ai_ortam)
    # çıkarım penceresine (son 14 gün) bariz bir aykırı gözlem enjekte et
    async with ai_ortam() as db:
        await search_path_ayarla(db, "alfa")
        makine = (await db.execute(select(Makine).where(Makine.kod == "AI-MAK-2"))).scalar_one()
        db.add(
            UretimVerisi(
                zaman=datetime.now(UTC) - timedelta(days=1, hours=2),
                makine_id=makine.id,
                planlanan_sure_dk=480.0,
                durus_sure_dk=460.0,
                toplam_adet=40,
                saglam_adet=15,
                ideal_cevrim_sn=60.0,
            )
        )
        await db.commit()
        makine_id = makine.id
    await _egitilmis(ai_ortam, "alfa", "anomali")
    cikarim = await _tahmin(ai_ortam, "alfa", "anomali")
    assert len(cikarim.sonuclar) >= 1
    assert cikarim.sonuclar[0]["makine_id"] == makine_id  # en aykırı ilk
    # outbox olayı aynı transaction'da yazıldı
    async with ai_ortam() as db:
        await search_path_ayarla(db, "alfa")
        olaylar = (
            (await db.execute(select(GidenOlay).where(GidenOlay.olay_turu == "anomali.tespit")))
            .scalars()
            .all()
        )
    assert len(olaylar) >= 1
    govde = olaylar[-1].govde
    assert govde["anomali_sayisi"] == len(cikarim.sonuclar)
    assert makine_id in govde["makineler"]
    assert govde["tahmin_id"] == cikarim.tahmin.id


async def test_ayni_anomali_tekrar_goruntulemede_yeniden_bildirilmez(
    ai_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    """GET /tahmin/anomali her açılışta çıkarım yapar; aynı bulgu için ikinci olay yazılmaz."""
    await egitim_yardimci._alfa_seed(ai_ortam)
    async with ai_ortam() as db:
        await search_path_ayarla(db, "alfa")
        makine = (await db.execute(select(Makine).where(Makine.kod == "AI-MAK-2"))).scalar_one()
        db.add(
            UretimVerisi(
                zaman=datetime.now(UTC) - timedelta(days=1, hours=2),
                makine_id=makine.id,
                planlanan_sure_dk=480.0,
                durus_sure_dk=460.0,
                toplam_adet=40,
                saglam_adet=15,
                ideal_cevrim_sn=60.0,
            )
        )
        await db.commit()
    await _egitilmis(ai_ortam, "alfa", "anomali")
    ilk = await _tahmin(ai_ortam, "alfa", "anomali")
    ikinci = await _tahmin(ai_ortam, "alfa", "anomali")
    assert ilk.sonuclar and ikinci.sonuclar
    assert ikinci.tahmin.id != ilk.tahmin.id  # tahmin geçmişi yine yazılır
    async with ai_ortam() as db:
        await search_path_ayarla(db, "alfa")
        olaylar = (
            (await db.execute(select(GidenOlay).where(GidenOlay.olay_turu == "anomali.tespit")))
            .scalars()
            .all()
        )
    assert len(olaylar) == 1
