"""S28 (ADR-0047): rapor hazır bildirimi gerçekten üretilir (API → outbox → bildirim merkezi).

Önceki test (``test_svb_bildirim``) olayı elle ekliyordu; rapor servisi olayı hiç yazmadığı için
kural tanımlı olduğu hâlde kullanıcıya "Raporunuz hazır" bildirimi hiç düşmüyordu.
"""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.db.tenancy import search_path_ayarla
from app.modules.bildirim.models import Bildirim
from app.modules.bildirim.uretici import tenant_uretici_turu
from tests.conftest import ALFA
from tests.test_s14_rapor_api import _giris, _h, rapor_istemci  # noqa: F401 — fikstür


async def test_rapor_hazir_bildirimi_isteyene_duser(
    rapor_istemci: AsyncClient,  # noqa: F811
    test_engine: AsyncEngine,
) -> None:
    h = _h("alfa", await _giris(rapor_istemci, ALFA))
    r = await rapor_istemci.post(
        "/api/v1/raporlar", json={"tur": "uretim", "bicim": "pdf", "gun": 7}, headers=h
    )
    assert r.status_code == 202, r.text
    kod = r.json()["data"]["kod"]

    sm = async_sessionmaker(test_engine, expire_on_commit=False)
    await tenant_uretici_turu(sm, "alfa")  # type: ignore[arg-type]

    async with sm() as s:
        await search_path_ayarla(s, "alfa")
        bildirimler = (
            (
                await s.execute(
                    select(Bildirim).where(
                        Bildirim.olay_turu == "rapor.hazir", Bildirim.baslik.contains(kod)
                    )
                )
            )
            .scalars()
            .all()
        )
    assert len(bildirimler) == 1  # yalnız raporu isteyene
    assert bildirimler[0].baslik == f"Raporunuz hazır: {kod}"
