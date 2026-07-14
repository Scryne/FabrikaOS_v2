"""Bildirim üretici çalıştırıcısı (S-VB / ADR-0021) — ayrı süreç (webhook relay deseni).

Tüm **aktif** tenant'larda outbox → bildirim fan-out'u koşar. Webhook relay ile
çakışmaz: relay ``giden_olaylar.durum``'u, üretici bağımsız ``bildirim_imleci``
yüksek-su-işaretini kullanır (iki tüketici, tek outbox).

Kullanım (repo kökünden, host .env ile):
    python backend/scripts/bildirim_uretici.py                # 10 sn aralıkla döngü
    python backend/scripts/bildirim_uretici.py --araligi 5    # 5 sn aralıkla döngü
    python backend/scripts/bildirim_uretici.py --tek-tur      # tek tur koş ve çık (e2e/test)
    python backend/scripts/bildirim_uretici.py --tenant alfa  # yalnız bir tenant
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.control_plane.models import Tenant
from app.core.config import get_settings
from app.core.logging import yapilandir_loglama
from app.modules.bildirim.kanallar import EPostaKanali
from app.modules.bildirim.uretici import tenant_uretici_turu

logger = logging.getLogger("app.bildirim.uretici.script")


async def tur(sm: async_sessionmaker, kanal: EPostaKanali, tenant: str | None) -> None:
    """Bir tam tur: aktif tenant listesini çek, her şemada üretici turu koş (hata izole)."""
    async with sm() as s:
        sonuc = await s.execute(select(Tenant.slug).where(Tenant.aktif))
        sluglar = [row for (row,) in sonuc.all() if tenant is None or row == tenant]
    for slug in sluglar:
        try:
            await tenant_uretici_turu(sm, slug, eposta_kanali=kanal)
        except Exception:  # noqa: BLE001 — tek tenant hatası döngüyü düşürmez
            logger.exception("bildirim üretici tenant hatası: %s", slug)


async def calistir(*, araligi: float, tek_tur: bool, tenant: str | None, db_url: str) -> None:
    engine = create_async_engine(db_url, poolclass=NullPool)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    kanal = EPostaKanali()
    try:
        logger.info("bildirim üretici başlıyor (araligi=%.1fs, tek_tur=%s)", araligi, tek_tur)
        while True:
            await tur(sm, kanal, tenant)
            if tek_tur:
                return
            await asyncio.sleep(araligi)
    finally:
        await engine.dispose()


def main() -> None:
    p = argparse.ArgumentParser(description="FabrikaOS bildirim üretici")
    p.add_argument("--araligi", type=float, default=10.0, help="tur aralığı (saniye)")
    p.add_argument("--tek-tur", action="store_true", help="tek tur koş ve çık")
    p.add_argument("--tenant", default=None, help="yalnız bu tenant için koş")
    args = p.parse_args()

    s = get_settings()
    yapilandir_loglama(s.log_level)
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(
        calistir(
            araligi=args.araligi,
            tek_tur=args.tek_tur,
            tenant=args.tenant,
            db_url=s.database_url,
        )
    )


if __name__ == "__main__":
    main()
