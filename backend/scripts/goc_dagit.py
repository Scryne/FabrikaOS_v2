"""Dağıtım adımı: göç fan-out'u (S20, ADR-0041). Ayrıntı: ``docs/operasyon/dr.md``.

    python backend/scripts/goc_dagit.py [--yedek-dizini /yedek/goc] [--tenant demo ...]

Public ağacı yükseltir, sonra her aktif tenant'ı ayrı ayrı (biri diğerini durdurmadan)
``head``'e taşır; ``--yedek-dizini`` verilirse her tenant'ın göç öncesi yedeği alınır.
Her tenant için bir JSON satırı yazar; en az bir tenant başarısızsa çıkış kodu 1.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.operasyon.dagitim import goc_dagit  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description="FabrikaOS göç fan-out dağıtımı")
    p.add_argument("--yedek-dizini", default=None, help="her tenant için göç öncesi yedek")
    p.add_argument("--tenant", action="append", default=None, help="yalnız bu tenant(lar)")
    args = p.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sonuclar = asyncio.run(
        goc_dagit(
            get_settings().database_url,
            yedek_dizini=Path(args.yedek_dizini) if args.yedek_dizini else None,
            sadece=args.tenant,
        )
    )
    for s in sonuclar:
        print(json.dumps(asdict(s), ensure_ascii=False))
    return 0 if all(s.basarili for s in sonuclar) else 1


if __name__ == "__main__":
    sys.exit(main())
