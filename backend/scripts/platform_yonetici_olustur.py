"""Platform yöneticisi açma/eşitleme aracı (S17 / ADR-0019).

İlk control-plane operatörü migration'da seed edilmez (parola migration'a gömülmez);
bu CLI ile açılır. E-posta üzerinden idempotenttir: varsa parolayı sıfırlar ve
hesabı yeniden aktifleştirir.

Kullanım (repo kökünden, host .env ile):
    python backend/scripts/platform_yonetici_olustur.py <eposta> <parola> [--ad "Ad Soyad"]
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.platform.kimlik_service import platform_yonetici_olustur


async def _calistir(args: argparse.Namespace) -> int:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sm() as s:
            yonetici = await platform_yonetici_olustur(
                s, eposta=args.eposta, parola=args.parola, ad_soyad=args.ad
            )
            await s.commit()
            print(f"platform yöneticisi hazır: {yonetici.eposta} (id={yonetici.id})")
            return 0
    finally:
        await engine.dispose()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("eposta")
    p.add_argument("parola")
    p.add_argument("--ad", default="", help="ad soyad (opsiyonel)")
    args = p.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(_calistir(args))


if __name__ == "__main__":
    raise SystemExit(main())
