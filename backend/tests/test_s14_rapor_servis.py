"""S14 rapor servisi entegrasyon testleri (gerçek DB, tenant-aware arka plan üretimi).

Alfa tenant'ına küçük bir veri seti ekilir; rapor kaydı ``kuyrukta`` açılır, arka plan
görevi (test modunda beklenerek) çalışır → ``hazir`` + nesne deposunda tenant-önekli
artefakt. Hata yolu ``basarisiz`` + ``hata`` mesajını doğrular.
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
from app.modules.dys.depolama import BellekNesneDepo, nesne_depo_ayarla
from app.modules.rapor import repository, service
from app.modules.rapor.models import Rapor
from app.modules.stok.models import Malzeme
from app.modules.uretim.models import Makine, UretimVerisi

_DEPO = BellekNesneDepo()


@pytest_asyncio.fixture
async def rapor_ortam(
    test_engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    sm = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)
    service.oturum_fabrikasi_ayarla(sm)
    service.es_zamanli_ayarla(True)
    nesne_depo_ayarla(_DEPO)
    redis_istemci.redis_ayarla(fakeredis.aioredis.FakeRedis(decode_responses=True))
    yield sm
    service.oturum_fabrikasi_ayarla(None)
    service.es_zamanli_ayarla(False)
    nesne_depo_ayarla(None)
    redis_istemci.redis_ayarla(None)


async def _alfa_seed(sm: async_sessionmaker[AsyncSession]) -> None:
    """Alfa'ya rapor verisi eker (idempotent: RS-MAK-1 varsa atlar)."""
    async with sm() as db:
        await search_path_ayarla(db, "alfa")
        mevcut = await db.execute(select(Makine).where(Makine.kod == "RS-MAK-1"))
        if mevcut.scalar_one_or_none() is not None:
            return
        mak = Makine(kod="RS-MAK-1", ad="Rapor Test Makine", durum="calisiyor")
        db.add(mak)
        await db.flush()
        simdi = datetime.now(UTC)
        for g in (2, 1):
            db.add(
                UretimVerisi(
                    zaman=simdi - timedelta(days=g),
                    makine_id=mak.id,
                    planlanan_sure_dk=480.0,
                    durus_sure_dk=30.0,
                    toplam_adet=100,
                    saglam_adet=95,
                    ideal_cevrim_sn=120.0,
                )
            )
        db.add(
            Malzeme(
                kod="RS-MLZ-1",
                ad="Rapor Test Malzeme",
                birim="adet",
                mevcut_miktar=Decimal(50),
                kritik_stok=Decimal(60),
            )
        )
        await db.commit()


async def _olustur_ve_uret(
    sm: async_sessionmaker[AsyncSession], slug: str, tur: str, bicim: str
) -> Rapor:
    async with sm() as db:
        await search_path_ayarla(db, slug)
        kayit = await service.rapor_olustur(db, tur=tur, bicim=bicim, gun=30, kullanici_id=None)
        await db.commit()
        kayit_id = kayit.id
    await service.rapor_uret_calistir(kayit_id, slug)
    async with sm() as db:
        await search_path_ayarla(db, slug)
        guncel = await repository.rapor_getir(db, kayit_id)
        assert guncel is not None
        return guncel


async def test_pdf_rapor_uretilir_hazir(
    rapor_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    await _alfa_seed(rapor_ortam)
    kayit = await _olustur_ve_uret(rapor_ortam, "alfa", "uretim", "pdf")
    assert kayit.durum == "hazir", kayit.hata
    assert kayit.kod.startswith("RP-")
    assert kayit.kod.endswith(f"{kayit.id:06d}")
    assert kayit.dosya_adi == f"{kayit.kod}.pdf"
    assert kayit.icerik_tipi == "application/pdf"
    assert kayit.nesne_anahtari == f"tenant_alfa/rapor/{kayit.id}/{kayit.dosya_adi}"
    assert kayit.boyut > 0
    assert kayit.satir_sayisi >= 2  # iki üretim günü
    assert kayit.uretim_suresi_sn is not None
    veri = _DEPO.indir(kayit.nesne_anahtari)
    assert veri.startswith(b"%PDF")
    assert len(veri) == kayit.boyut


async def test_xlsx_rapor_uretilir(
    rapor_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    await _alfa_seed(rapor_ortam)
    kayit = await _olustur_ve_uret(rapor_ortam, "alfa", "stok", "xlsx")
    assert kayit.durum == "hazir", kayit.hata
    assert kayit.icerik_tipi.endswith("spreadsheetml.sheet")
    assert _DEPO.indir(kayit.nesne_anahtari)[:2] == b"PK"  # zip sihirli baytı


async def test_tum_turler_uretilir(
    rapor_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    await _alfa_seed(rapor_ortam)
    for tur in ("uretim", "stok", "kalite", "enerji", "isemri"):
        kayit = await _olustur_ve_uret(rapor_ortam, "alfa", tur, "xlsx")
        assert kayit.durum == "hazir", (tur, kayit.hata)
        assert kayit.nesne_anahtari.startswith("tenant_alfa/rapor/")


async def test_uretim_hatasi_basarisiz_isaretler(
    rapor_ortam: async_sessionmaker[AsyncSession],
    test_db: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    await _alfa_seed(rapor_ortam)

    def _patlat(*_args: object, **_kwargs: object) -> bytes:
        raise RuntimeError("kasıtlı üretim hatası")

    monkeypatch.setattr(service, "_uret", _patlat)
    kayit = await _olustur_ve_uret(rapor_ortam, "alfa", "uretim", "pdf")
    assert kayit.durum == "basarisiz"
    assert "kasıtlı üretim hatası" in kayit.hata
    assert kayit.uretim_suresi_sn is not None


async def test_verisiz_tenant_bos_rapor_hazir(
    rapor_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    # beta'da üretim verisi yok → boş tablolu ama geçerli rapor (hazir).
    kayit = await _olustur_ve_uret(rapor_ortam, "beta", "uretim", "pdf")
    assert kayit.durum == "hazir", kayit.hata
    assert kayit.satir_sayisi == 0
    assert kayit.nesne_anahtari.startswith("tenant_beta/rapor/")


async def test_gecersiz_tur_ve_bicim_reddedilir(
    rapor_ortam: async_sessionmaker[AsyncSession], test_db: str
) -> None:
    from app.core.exceptions import DogrulamaHatasi

    async with rapor_ortam() as db:
        await search_path_ayarla(db, "alfa")
        with pytest.raises(DogrulamaHatasi):
            await service.rapor_olustur(
                db, tur="bilinmeyen", bicim="pdf", gun=30, kullanici_id=None
            )
        with pytest.raises(DogrulamaHatasi):
            await service.rapor_olustur(db, tur="uretim", bicim="docx", gun=30, kullanici_id=None)
