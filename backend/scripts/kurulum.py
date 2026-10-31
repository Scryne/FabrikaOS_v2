"""İlk kurulum / güncelleme sonrası tek komut (S21, ADR-0042). İdempotenttir; tekrar koşmak güvenli.

    python backend/scripts/kurulum.py                       # şemaları head'e getir
    python backend/scripts/kurulum.py --tenant fabrika-a --ad "Fabrika A" \\
        --admin-eposta admin@fabrika-a.com.tr --plan profesyonel
        (yönetici parolası KURULUM_ADMIN_PAROLA ortamından)

Adımlar: (1) public şema + plan kataloğu, (2) mevcut tenant'lar tenant başına yalıtılmış göç
(``goc_dagit``), (3) istenirse yeni tenant provizyonu (var olan tenant'a dokunmaz). Demo verisi
ayrıca: ``python backend/scripts/demo_verisi.py --base-url http://localhost:8000``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.control_plane.provizyon import tenant_provizyonla  # noqa: E402
from app.core.config import get_settings  # noqa: E402
from app.operasyon.dagitim import goc_dagit  # noqa: E402


async def _ana(args: argparse.Namespace) -> int:
    db_url = get_settings().database_url
    sonuclar = await goc_dagit(db_url)  # public yükseltme + tenant fan-out
    for s in sonuclar:
        print(json.dumps({"adim": "goc", **asdict(s)}, ensure_ascii=False))
    hata = not all(s.basarili for s in sonuclar)
    if args.tenant:
        parola = os.environ.get("KURULUM_ADMIN_PAROLA")
        if not parola or not args.admin_eposta:
            print("Tenant için --admin-eposta ve KURULUM_ADMIN_PAROLA gerekli.", file=sys.stderr)
            return 2
        await tenant_provizyonla(
            slug=args.tenant,
            ad=args.ad or args.tenant,
            admin_eposta=args.admin_eposta,
            admin_parola=parola,
            plan_kodu=args.plan,
            db_url=db_url,
        )
        print(
            json.dumps(
                {"adim": "tenant", "slug": args.tenant, "plan": args.plan}, ensure_ascii=False
            )
        )
    return 1 if hata else 0


def main() -> int:
    p = argparse.ArgumentParser(description="FabrikaOS kurulum")
    p.add_argument("--tenant", default=None, help="provizyonlanacak tenant slug'ı")
    p.add_argument("--ad", default=None)
    p.add_argument("--admin-eposta", default=None)
    p.add_argument(
        "--plan", default="deneme", help="plan kodu (deneme, temel, profesyonel, kurumsal)"
    )
    args = p.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(_ana(args))


if __name__ == "__main__":
    sys.exit(main())
