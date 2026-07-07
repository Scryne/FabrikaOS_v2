"""S13 eğitim servisi entegrasyon testleri (gerçek DB, tenant-aware arka plan akışı).

Alfa tenant'ına üretim/arıza/stok verisi ekilir; dört model türü **tenant verisiyle**
eğitilir (hazir + aktif + sürümlü artefakt). Az verili beta ``basarisiz`` yolunu ve
izolasyonu doğrular.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import fakeredis.aioredis
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.core.security import redis_istemci
from app.modules.ai import artefakt, repository, service
from app.modules.ai.models import ModelKaydi
from app.modules.dys.depolama import BellekNesneDepo, nesne_depo_ayarla
from app.modules.stok.models import Malzeme, StokHareketi
from app.modules.uretim.models import ArizaKaydi, Makine, UretimVerisi

pytestmark = pytest.mark.asyncio

_DEPO = BellekNesneDepo()


@pytest_asyncio.fixture
async def ai_ortam(
    test_engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    sm = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    service.oturum_fabrikasi_ayarla(sm)
    service.es_zamanli_ayarla(True)
    nesne_depo_ayarla(_DEPO)
    artefakt.onbellek_temizle()
    redis_istemci.redis_ayarla(fakeredis.aioredis.FakeRedis(decode_responses=True))
    yield sm
    service.oturum_fabrikasi_ayarla(None)
    service.es_zamanli_ayarla(False)
    nesne_depo_ayarla(None)
    artefakt.onbellek_temizle()
    redis_istemci.redis_ayarla(None)


async def _alfa_seed(sm: async_sessionmaker[AsyncSession]) -> None:
    """Alfa'ya AI eğitim verisi eker (idempotent: AI-MAK-1 varsa atlar)."""
    async with sm() as db:
        await search_path_ayarla(db, "alfa")
        mevcut = await db.execute(select(Makine).where(Makine.kod == "AI-MAK-1"))
        if mevcut.scalar_one_or_none() is not None:
            return
        simdi = datetime.now(UTC)
        makine_ids: list[int] = []
        for m in (1, 2):
            mak = Makine(kod=f"AI-MAK-{m}", ad=f"AI Test Makine {m}", durum="calisiyor")
            db.add(mak)
            await db.flush()
            makine_ids.append(mak.id)
        for m_idx, mid in enumerate(makine_ids):
            for g in range(30, 0, -1):
                # makine 1 periyodik olarak yüksek duruşlu (arıza öncesi desen)
                durus = 30.0 + (150.0 if (m_idx == 0 and g % 10 < 3) else 0.0)
                db.add(
                    UretimVerisi(
                        zaman=simdi - timedelta(days=g),
                        makine_id=mid,
                        planlanan_sure_dk=480.0,
                        durus_sure_dk=durus,
                        toplam_adet=400,
                        saglam_adet=392 - 2 * m_idx,
                        ideal_cevrim_sn=60.0,
                    )
                )
        # makine 1'e iki arıza (kestirimci bakım etiketi + sayaçlar için)
        db.add(ArizaKaydi(makine_id=makine_ids[0], baslangic=simdi - timedelta(days=20)))
        db.add(ArizaKaydi(makine_id=makine_ids[0], baslangic=simdi - timedelta(days=8)))
        # stok: 12 gün, günde 10 birim çıkış
        malzeme = Malzeme(
            kod="AI-MLZ-1",
            ad="AI Test Malzeme",
            birim="adet",
            mevcut_miktar=Decimal(120),
            min_stok=Decimal(10),
            kritik_stok=Decimal(20),
        )
        db.add(malzeme)
        await db.flush()
        bakiye = Decimal(240)
        for g in range(12, 0, -1):
            bakiye -= Decimal(10)
            db.add(
                StokHareketi(
                    malzeme_id=malzeme.id,
                    tur="cikis",
                    miktar=Decimal(10),
                    bakiye_sonrasi=bakiye,
                    olusturma_tarihi=simdi - timedelta(days=g),
                )
            )
        await db.commit()


async def _egit_ve_getir(sm: async_sessionmaker[AsyncSession], slug: str, tur: str) -> ModelKaydi:
    async with sm() as db:
        await search_path_ayarla(db, slug)
        kayit = await service.egitim_baslat(db, tur=tur, kullanici_id=None)
        await db.commit()
        kayit_id = kayit.id
    await service.egitim_calistir(kayit_id, slug, tur)
    async with sm() as db:
        await search_path_ayarla(db, slug)
        guncel = await repository.kayit_getir(db, kayit_id)
        assert guncel is not None
        return guncel


async def test_oee_egitimi_hazir_aktif_artefaktli(
    ai_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    await _alfa_seed(ai_ortam)
    kayit = await _egit_ve_getir(ai_ortam, "alfa", "oee")
    assert kayit.durum == "hazir"
    assert kayit.aktif is True
    assert kayit.nesne_anahtari.startswith("tenant_alfa/model/oee/")
    assert kayit.metrikler is not None and kayit.metrikler["satir_sayisi"] > 0
    assert kayit.veri_ozeti is not None and kayit.veri_ozeti["artefakt_bayt"] > 0
    assert kayit.egitim_suresi_sn is not None
    assert _DEPO.var_mi(kayit.nesne_anahtari)  # artefakt gerçekten depoda


async def test_tum_turler_tenant_verisiyle_egitilir(
    ai_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    await _alfa_seed(ai_ortam)
    for tur in ("kestirimci_bakim", "anomali", "stok"):
        kayit = await _egit_ve_getir(ai_ortam, "alfa", tur)
        assert kayit.durum == "hazir", (tur, kayit.hata)
        assert kayit.nesne_anahtari.startswith(f"tenant_alfa/model/{tur}/")


async def test_verisiz_tenant_egitimi_basarisiz(
    ai_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    kayit = await _egit_ve_getir(ai_ortam, "beta", "oee")
    assert kayit.durum == "basarisiz"
    assert kayit.aktif is False
    assert "En az" in kayit.hata  # YetersizVeri mesajı kullanıcıya açık
    assert kayit.egitim_suresi_sn is not None


async def test_yeni_surum_aktifi_devreder(
    ai_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    await _alfa_seed(ai_ortam)
    ilk = await _egit_ve_getir(ai_ortam, "alfa", "oee")
    ikinci = await _egit_ve_getir(ai_ortam, "alfa", "oee")
    assert ikinci.surum > ilk.surum
    assert ikinci.aktif is True
    async with ai_ortam() as db:
        await search_path_ayarla(db, "alfa")
        eski = await repository.kayit_getir(db, ilk.id)
        aktif = await repository.aktif_kayit(db, "oee")
    assert eski is not None and eski.aktif is False  # rotasyon
    assert aktif is not None and aktif.id == ikinci.id


async def test_izolasyon_beta_alfa_modellerini_gormez(
    ai_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    await _alfa_seed(ai_ortam)
    await _egit_ve_getir(ai_ortam, "alfa", "oee")
    async with ai_ortam() as db:
        await search_path_ayarla(db, "beta")
        beta_kayitlar = await repository.kayit_listele(db)
    # beta şemasında alfa'nın hazir modelleri görünmez (yalnız kendi kayıtları olabilir)
    assert all(k.durum != "hazir" for k in beta_kayitlar)
    assert all(not k.nesne_anahtari.startswith("tenant_alfa/") for k in beta_kayitlar)
