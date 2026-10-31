"""S20 göç fan-out dağıtımı: tenant başına yalıtım, rapor, göç öncesi yedek (ADR-0041)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.control_plane.provizyon import tenant_provizyonla
from app.core.db import fanout
from app.operasyon.dagitim import goc_dagit
from app.operasyon.yedek import manifest_oku
from tests.conftest import TEST_URL

SLUG = "dagitimt"
ONCEKI = "a7c3e9d25f18"  # S25-A; head'den bir önceki revizyonlardan


def _head() -> str:
    kok = Path(fanout.__file__).resolve().parents[4]
    cfg = Config(str(kok / "alembic.ini"), ini_section="tenant")
    head = ScriptDirectory.from_config(cfg).get_current_head()
    assert head is not None
    return head


@pytest.fixture(scope="module")
def eski_tenant(test_db: str) -> str:
    asyncio.run(
        tenant_provizyonla(
            slug=SLUG,
            ad="Dağıtım",
            admin_eposta="admin@dagitimt.test",
            admin_parola="Dagitim12345!",
            plan_kodu="kurumsal",
            db_url=TEST_URL,
        )
    )
    fanout.tenant_indir_tek(SLUG, ONCEKI, db_url=TEST_URL)
    return SLUG


async def test_eski_tenant_yedeklenip_head_e_yukseltilir(eski_tenant: str, tmp_path: Path) -> None:
    sonuclar = await goc_dagit(TEST_URL, yedek_dizini=tmp_path, sadece=[eski_tenant])
    assert len(sonuclar) == 1
    s = sonuclar[0]
    assert s.basarili, s.hata
    assert (s.onceki, s.sonraki) == (ONCEKI, _head())
    # Göç öncesi yedek eski revizyonu taşıyor: bozulan göç bu dosyayla geri alınır.
    assert s.yedek is not None
    assert manifest_oku(Path(s.yedek)).alembic_revizyonu == ONCEKI


async def test_bir_tenantin_hatasi_digerlerini_durdurmaz(eski_tenant: str) -> None:
    await asyncio.to_thread(fanout.tenant_indir_tek, eski_tenant, ONCEKI, db_url=TEST_URL)

    def yukselt(slug: str, *, db_url: str) -> None:
        if slug == "alfa":
            raise RuntimeError("bozuk göç")
        fanout.tenant_yukselt_tek(slug, db_url=db_url)

    sonuclar = {
        s.slug: s for s in await goc_dagit(TEST_URL, sadece=["alfa", eski_tenant], yukselt=yukselt)
    }
    assert not sonuclar["alfa"].basarili
    assert "bozuk göç" in (sonuclar["alfa"].hata or "")
    assert sonuclar["alfa"].sonraki == _head()  # dokunulmadı, zaten head'deydi
    assert sonuclar[eski_tenant].basarili
    assert sonuclar[eski_tenant].sonraki == _head()
