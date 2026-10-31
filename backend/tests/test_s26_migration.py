"""S26 migration fan-out testi: S26-A (SPC/kalibrasyon) + S26-B (İSG/İK) up/down (tenant_alfa)."""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from app.core.db import fanout
from tests.conftest import TEST_URL

pytestmark = pytest.mark.asyncio

_DSN = TEST_URL.replace("postgresql+asyncpg://", "postgresql://")
_S25 = "b8d4f0e36a29"  # S25 head — S26 nesneleri bunun üstünde
_S26A = "c3e5a7f9b1d2"
_TABLOLAR_A = (
    "olcum_cihazlari",
    "kalibrasyon_kayitlari",
    "kontrol_planlari",
    "kontrol_karakteristikleri",
    "spc_alt_gruplari",
)
_TABLOLAR_B = (
    "isg_egitimleri",
    "isg_egitim_katilimlari",
    "isg_egitim_gereksinimleri",
    "kkd_gereksinimleri",
    "acil_durum_tatbikatlari",
    "personel_kontrol_listeleri",
)
_SUTUNLAR_B = (
    ("personel", "yonetici_id"),
    ("zimmetler", "kategori"),
    ("uygunsuzluklar", "kaynak_kaza_id"),
)


async def _sorgu(sql: str, *arg: object) -> bool:
    conn = await asyncpg.connect(_DSN)
    try:
        return bool(await conn.fetchval(sql, *arg))
    finally:
        await conn.close()


async def _tablo(t: str) -> bool:
    return await _sorgu("SELECT to_regclass($1) IS NOT NULL", f"tenant_alfa.{t}")


async def _sutun(t: str, s: str) -> bool:
    return await _sorgu(
        "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
        "WHERE table_schema = 'tenant_alfa' AND table_name = $1 AND column_name = $2)",
        t,
        s,
    )


async def test_s26_up_down(test_db: str) -> None:
    for t in (*_TABLOLAR_A, *_TABLOLAR_B):
        assert await _tablo(t), t
    for t, s in _SUTUNLAR_B:
        assert await _sutun(t, s), (t, s)

    # S26-B'yi geri al: yalnız B nesneleri gider, A kalır.
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _S26A, db_url=TEST_URL)
    for t in _TABLOLAR_B:
        assert not await _tablo(t), t
    for t, s in _SUTUNLAR_B:
        assert not await _sutun(t, s), (t, s)
    for t in _TABLOLAR_A:
        assert await _tablo(t), t

    # S26-A'yı da geri al.
    await asyncio.to_thread(fanout.tenant_indir_tek, "alfa", _S25, db_url=TEST_URL)
    for t in _TABLOLAR_A:
        assert not await _tablo(t), t
    assert not await _sutun("uygunsuzluklar", "tedarikci_firma_id")

    # head'e geri çık (sonraki testler için durumu geri yükle).
    await asyncio.to_thread(fanout.tenant_yukselt_tek, "alfa", "head", db_url=TEST_URL)
    assert await _tablo("acil_durum_tatbikatlari")
    assert await _sutun("personel", "yonetici_id")
