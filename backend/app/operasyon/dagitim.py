"""Dağıtımda göç fan-out'u: tenant başına yalıtılmış, raporlu, isteğe bağlı ön yedekli (S20).

``alembic --name tenant upgrade head`` bütün tenant'ları tek koşuda yükseltir: biri hata
verirse koşu durur, kalanlar eski revizyonda kalır ve hangisinin nerede kaldığı log'dan
çıkarılır. Bu akış her tenant'ı ayrı yükseltir, birinin hatası diğerlerini durdurmaz, her
tenant için revizyon/süre/hata raporlanır ve (``yedek_dizini`` verilirse) yükseltmeden hemen
önce o tenant'ın yedeği alınır: bozulan bir göç tek komutla geri alınabilir.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import asyncpg

from app.core.db import fanout
from app.core.db.tenancy import sema_adi
from app.operasyon.yedek import asyncpg_dsn, tenant_yedekle


@dataclass
class TenantGocSonucu:
    slug: str
    onceki: str | None
    sonraki: str | None
    basarili: bool
    sure_sn: float
    yedek: str | None = None
    hata: str | None = None


async def _revizyon(conn: asyncpg.Connection, slug: str) -> str | None:
    sema = sema_adi(slug)
    var = await conn.fetchval(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_schema = $1 AND table_name = 'alembic_version'",
        sema,
    )
    if not var:
        return None
    deger = await conn.fetchval(f'SELECT version_num FROM "{sema}".alembic_version')
    return None if deger is None else str(deger)


async def goc_dagit(
    db_url: str,
    *,
    yedek_dizini: Path | None = None,
    sadece: list[str] | None = None,
    yukselt: Callable[..., None] = fanout.tenant_yukselt_tek,
) -> list[TenantGocSonucu]:
    """Public ağacı, ardından her aktif tenant'ı ayrı ayrı ``head``'e yükseltir."""
    await asyncio.to_thread(fanout.public_yukselt, db_url=db_url)
    dsn = asyncpg_dsn(db_url)
    conn = await asyncpg.connect(dsn)
    try:
        sluglar = [
            r["slug"]
            for r in await conn.fetch("SELECT slug FROM public.tenant WHERE aktif ORDER BY slug")
            if sadece is None or r["slug"] in sadece
        ]
        sonuclar: list[TenantGocSonucu] = []
        for slug in sluglar:
            t0 = time.perf_counter()
            onceki = await _revizyon(conn, slug)
            yedek: str | None = None
            try:
                if yedek_dizini is not None:
                    damga = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                    hedef = yedek_dizini / f"{slug}-{damga}-goc-oncesi.zip"
                    await tenant_yedekle(dsn, slug, hedef)
                    yedek = str(hedef)
                await asyncio.to_thread(yukselt, slug, db_url=db_url)
                sonuclar.append(
                    TenantGocSonucu(
                        slug,
                        onceki,
                        await _revizyon(conn, slug),
                        True,
                        round(time.perf_counter() - t0, 3),
                        yedek,
                    )
                )
            except Exception as exc:  # noqa: BLE001 — bir tenant diğerlerini durdurmaz
                sonuclar.append(
                    TenantGocSonucu(
                        slug,
                        onceki,
                        await _revizyon(conn, slug),
                        False,
                        round(time.perf_counter() - t0, 3),
                        yedek,
                        f"{type(exc).__name__}: {exc}",
                    )
                )
    finally:
        await conn.close()

    basarili = [s.slug for s in sonuclar if s.basarili]
    if basarili:
        # İzin kataloğu uzlaştırması (yeni sprintin izin kodları mevcut tenant'lara iner);
        # tam fan-out'un yaptığı adım, burada yalnız yükseltilenler için.
        from app.control_plane.uzlastirma import tum_tenantlari_uzlastir

        await tum_tenantlari_uzlastir(db_url=db_url)
    return sonuclar
