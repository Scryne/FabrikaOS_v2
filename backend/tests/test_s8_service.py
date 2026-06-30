"""S8 ingestion servisi — idempotency, bilinmeyen cihaz/makine, OEE'ye akış, tenant izolasyonu."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.ingestion.service import olcum_yaz_toplu
from app.modules.saha import repository
from app.modules.saha.models import Cihaz
from app.modules.saha.schemas import OlcumPaketi
from app.modules.uretim.models import Makine, UretimVerisi

pytestmark = pytest.mark.asyncio


def _paket(makine_kod: str, *, toplam: int = 100, saglam: int = 98) -> OlcumPaketi:
    return OlcumPaketi(
        olcum_id=uuid.uuid4(),
        makine_kod=makine_kod,
        zaman=datetime.now(UTC),
        vardiya="A",
        planlanan_sure_dk=60.0,
        durus_sure_dk=5.0,
        toplam_adet=toplam,
        saglam_adet=saglam,
        ideal_cevrim_sn=30.0,
    )


async def _oturum(engine: object, slug: str) -> AsyncSession:
    sm = async_sessionmaker(engine, expire_on_commit=False)  # type: ignore[arg-type]
    s = sm()
    await search_path_ayarla(s, slug)
    return s


@pytest_asyncio.fixture
async def alfa(test_engine: object) -> AsyncIterator[AsyncSession]:
    s = await _oturum(test_engine, "alfa")
    await repository.cihaz_ekle(s, Cihaz(kod="GW-SVC", ad="Servis GW"))
    s.add(Makine(kod="MAK-SVC", ad="Servis Makine"))
    await s.flush()
    yield s
    await s.rollback()
    await s.close()


async def test_yazma_oee_girdisi_olusturur(alfa: AsyncSession) -> None:
    sonuc = await olcum_yaz_toplu(alfa, cihaz_kod="GW-SVC", paketler=[_paket("MAK-SVC")])
    assert sonuc.yazilan == 1 and sonuc.atlanan == 0 and sonuc.hatali == 0
    sayi = await alfa.scalar(select(func.count()).select_from(UretimVerisi))
    assert sayi == 1


async def test_idempotent_replay_cift_yazmaz(alfa: AsyncSession) -> None:
    p = _paket("MAK-SVC")
    ilk = await olcum_yaz_toplu(alfa, cihaz_kod="GW-SVC", paketler=[p])
    tekrar = await olcum_yaz_toplu(alfa, cihaz_kod="GW-SVC", paketler=[p])
    assert ilk.yazilan == 1
    assert tekrar.yazilan == 0 and tekrar.atlanan == 1


async def test_bilinmeyen_cihaz_yazmaz(alfa: AsyncSession) -> None:
    sonuc = await olcum_yaz_toplu(alfa, cihaz_kod="YOK", paketler=[_paket("MAK-SVC")])
    assert sonuc.yazilan == 0 and sonuc.hatali == 1


async def test_bilinmeyen_makine_hatali(alfa: AsyncSession) -> None:
    sonuc = await olcum_yaz_toplu(alfa, cihaz_kod="GW-SVC", paketler=[_paket("YOK-MAK")])
    assert sonuc.yazilan == 0 and sonuc.hatali == 1


async def test_tenant_izolasyonu(test_engine: object) -> None:
    # alfa'da cihaz+makine var; beta'da YOK → beta'ya yazılmaz (çapraz-tenant sızıntı yok).
    beta = await _oturum(test_engine, "beta")
    try:
        sonuc = await olcum_yaz_toplu(beta, cihaz_kod="GW-SVC", paketler=[_paket("MAK-SVC")])
        assert sonuc.yazilan == 0  # beta şemasında GW-SVC cihazı yok
    finally:
        await beta.rollback()
        await beta.close()
