"""Entitlement/plan operasyon aracı (S16 / ADR-0018) — platform paneli (S17) gelene dek CLI.

Kullanım (repo kökünden, host .env ile):
    python backend/scripts/entitlement_ayarla.py <slug> goster
    python backend/scripts/entitlement_ayarla.py <slug> modul <kod> ac|kapat|sifirla
    python backend/scripts/entitlement_ayarla.py <slug> ozellik <kod> ac|kapat|sifirla
    python backend/scripts/entitlement_ayarla.py <slug> plan <plan_kodu>

Değişiklik ANINDA etkilidir (backend önbelleksiz sorgular); sunucu yeniden başlatılmaz.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.control_plane import entitlement_service
from app.control_plane.models import Tenant
from app.control_plane.moduller import PLAN_KATALOGU
from app.core.config import get_settings

_DURUMLAR = {"ac": True, "kapat": False, "sifirla": None}


async def _calistir(args: argparse.Namespace) -> int:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sm() as s:
            tenant = (
                await s.execute(select(Tenant).where(Tenant.slug == args.slug))
            ).scalar_one_or_none()
            if tenant is None:
                print(f"HATA: tenant bulunamadı: {args.slug!r}")
                return 1

            if args.komut == "modul":
                await entitlement_service.modul_hakki_ayarla(
                    s, tenant.id, args.kod, _DURUMLAR[args.durum]
                )
                await s.commit()
            elif args.komut == "ozellik":
                await entitlement_service.ozellik_bayragi_ayarla(
                    s, tenant.id, args.kod, _DURUMLAR[args.durum]
                )
                await s.commit()
            elif args.komut == "plan":
                if args.plan_kodu not in PLAN_KATALOGU:
                    print(f"HATA: katalogda olmayan plan: {args.plan_kodu!r}")
                    return 1
                ab = tenant.gecerli_abonelik
                if ab is None:
                    print("HATA: tenant'ın geçerli aboneliği yok")
                    return 1
                ab.plan_kodu = args.plan_kodu
                await s.commit()

            # Her komuttan sonra etkin durumu göster.
            ab = tenant.gecerli_abonelik
            plan = await entitlement_service.plan_getir(s, tenant)
            moduller = await entitlement_service.tenant_etkin_moduller(s, tenant)
            ozellikler = await entitlement_service.tenant_etkin_ozellikler(s, tenant)
            haklar = await entitlement_service.hak_haritasi_getir(s, tenant.id)

            print(f"tenant : {tenant.slug} ({tenant.ad})")
            print(f"plan   : {plan.kod if plan else '—'} (durum={ab.durum if ab else '—'})")
            print("moduller:")
            for kod, acik in sorted(moduller.items()):
                isaret = "AÇIK " if acik else "KAPALI"
                kaynak = " [hak]" if kod in haklar else ""
                print(f"  {isaret} {kod}{kaynak}")
            print("ozellikler:")
            for kod, acik in sorted(ozellikler.items()):
                print(f"  {'AÇIK ' if acik else 'KAPALI'} {kod}")
            return 0
    finally:
        await engine.dispose()


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("slug", help="tenant slug (ör. demo)")
    alt = p.add_subparsers(dest="komut", required=True)

    alt.add_parser("goster", help="etkin modül/özellik durumunu listele")

    pm = alt.add_parser("modul", help="modül override'ı ayarla")
    pm.add_argument("kod")
    pm.add_argument("durum", choices=sorted(_DURUMLAR))

    po = alt.add_parser("ozellik", help="özellik bayrağı override'ı ayarla")
    po.add_argument("kod")
    po.add_argument("durum", choices=sorted(_DURUMLAR))

    pp = alt.add_parser("plan", help="geçerli aboneliğin planını değiştir")
    pp.add_argument("plan_kodu", choices=sorted(PLAN_KATALOGU))

    args = p.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(_calistir(args))


if __name__ == "__main__":
    raise SystemExit(main())
