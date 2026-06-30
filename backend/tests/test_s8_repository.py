"""S8 saha repository birim testleri (tenant_alfa oturumu üzerinden)."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.modules.saha import repository
from app.modules.saha.models import Cihaz
from app.modules.uretim.models import Makine

pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def oturum(test_engine: object) -> AsyncIterator[AsyncSession]:
    sm = async_sessionmaker(test_engine, expire_on_commit=False)  # type: ignore[arg-type]
    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        yield s
        await s.rollback()


async def test_cihaz_ekle_ve_kod_ile_bul(oturum: AsyncSession) -> None:
    await repository.cihaz_ekle(oturum, Cihaz(kod="GW-REPO-1", ad="Gateway 1"))
    bulunan = await repository.cihaz_kod_ile(oturum, "GW-REPO-1")
    assert bulunan is not None and bulunan.ad == "Gateway 1"
    assert await repository.cihaz_kod_var_mi(oturum, "GW-REPO-1")


async def test_makine_id_kod_ile(oturum: AsyncSession) -> None:
    m = Makine(kod="MAK-REPO-1", ad="Makine 1")
    oturum.add(m)
    await oturum.flush()
    assert await repository.makine_id_kod_ile(oturum, "MAK-REPO-1") == m.id
    assert await repository.makine_id_kod_ile(oturum, "YOK") is None


async def test_olcum_isaretle_idempotent(oturum: AsyncSession) -> None:
    oid = uuid.uuid4()
    assert await repository.olcum_isaretle(oturum, oid, 1) is True
    assert await repository.olcum_isaretle(oturum, oid, 1) is False
