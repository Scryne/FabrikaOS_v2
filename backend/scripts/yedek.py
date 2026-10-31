"""FabrikaOS tenant yedek aracı (S20, ADR-0041). Ayrıntı: ``docs/operasyon/dr.md``.

    python backend/scripts/yedek.py al demo --dizin /yedek
    python backend/scripts/yedek.py tumu --dizin /yedek
    python backend/scripts/yedek.py dogrula /yedek/demo-20261101T020000Z.zip
    python backend/scripts/yedek.py geri-yukle /yedek/demo-....zip [--hedef demo] --evet
    python backend/scripts/yedek.py tatbikat demo --dizin /yedek \
        [--rapor docs/operasyon/tatbikatlar]
    python backend/scripts/yedek.py staging /yedek/demo-....zip --hedef demo-staging \\
        --yonetici-eposta yonetici@staging.test   (parola STAGING_YONETICI_PAROLA ortamından)

Veritabanı adresi ``DATABASE_URL`` (uygulamayla aynı) ortamından okunur.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncpg  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.operasyon.anonim import tenant_anonimlestir  # noqa: E402
from app.operasyon.yedek import (  # noqa: E402
    YedekHatasi,
    asyncpg_dsn,
    tenant_geri_yukle,
    tenant_yedekle,
    yedek_dogrula,
)


def _dosya_adi(dizin: Path, slug: str) -> Path:
    return dizin / f"{slug}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.zip"


def _yaz(veri: object) -> None:
    print(json.dumps(veri, ensure_ascii=False, default=str))


async def _al(db_url: str, slug: str, dizin: Path) -> Path:
    hedef = _dosya_adi(dizin, slug)
    m = await tenant_yedekle(asyncpg_dsn(db_url), slug, hedef)
    _yaz(
        {
            "islem": "al",
            "slug": slug,
            "dosya": str(hedef),
            "revizyon": m.alembic_revizyonu,
            "tablo": len(m.tablolar),
            "satir": m.toplam_satir,
            "sure_sn": m.sure_sn,
        }
    )
    return hedef


async def _tumu(db_url: str, dizin: Path) -> int:
    conn = await asyncpg.connect(asyncpg_dsn(db_url))
    try:
        sluglar = [
            r["slug"]
            for r in await conn.fetch("SELECT slug FROM public.tenant WHERE aktif ORDER BY slug")
        ]
    finally:
        await conn.close()
    hata = 0
    for slug in sluglar:
        try:
            await _al(db_url, slug, dizin)
        except Exception as exc:  # noqa: BLE001 — bir tenant diğerlerini durdurmaz
            hata += 1
            _yaz({"islem": "al", "slug": slug, "hata": f"{type(exc).__name__}: {exc}"})
    return 1 if hata else 0


def _tatbikat_raporu(dizin: Path, slug: str, dosya: Path, rapor: dict[str, object]) -> Path:
    dizin.mkdir(parents=True, exist_ok=True)
    tarih = datetime.now(UTC)
    yol = dizin / f"{tarih:%Y-%m-%d}-{slug}.md"
    adimlar = "\n".join(f"| {k} | {v} |" for k, v in dict(rapor["adimlar"]).items())  # type: ignore[call-overload]
    yol.write_text(
        f"""# Geri yükleme tatbikatı — {slug} ({tarih:%Y-%m-%d %H:%M} UTC)

- Yedek: `{dosya.name}` (revizyon `{rapor["revizyon"]}`)
- Tablo / satır: {rapor["tablo"]} / {rapor["satir"]}
- Sonuç: **başarılı** — geçici şemaya kuruldu, satır sayısı ve içerik parmak izi yedekle birebir,
  canlı şemaya dokunulmadı.
- Toplam geri yükleme süresi (RTO'nun veri kısmı): **{rapor["sure_sn"]} sn** (hedef ≤ 2 sa)

| Adım | Süre (sn) |
|---|---|
{adimlar}
""",
        encoding="utf-8",
    )
    return yol


async def _ana(args: argparse.Namespace) -> int:
    db_url = get_settings().database_url
    try:
        if args.komut == "al":
            await _al(db_url, args.slug, Path(args.dizin))
        elif args.komut == "tumu":
            return await _tumu(db_url, Path(args.dizin))
        elif args.komut == "dogrula":
            m = await asyncio.to_thread(yedek_dogrula, Path(args.dosya))
            _yaz(
                {
                    "islem": "dogrula",
                    "dosya": args.dosya,
                    "slug": m.slug,
                    "revizyon": m.alembic_revizyonu,
                    "satir": m.toplam_satir,
                    "alindi": m.alindi,
                    "sonuc": "saglam",
                }
            )
        elif args.komut == "geri-yukle":
            if not args.evet:
                print(
                    "Canlı şema yer değiştirecek (eski şema eski_<slug>_<zaman> olarak saklanır). "
                    "Onaylamak için --evet ekleyin.",
                    file=sys.stderr,
                )
                return 2
            r = await tenant_geri_yukle(db_url, Path(args.dosya), args.hedef)
            _yaz({"islem": "geri-yukle", **asdict(r)})
        elif args.komut == "tatbikat":
            dosya = await _al(db_url, args.slug, Path(args.dizin))
            r = await tenant_geri_yukle(db_url, dosya, args.slug, yalniz_dogrula=True)
            _yaz({"islem": "tatbikat", **asdict(r)})
            if args.rapor:
                print(f"rapor: {_tatbikat_raporu(Path(args.rapor), args.slug, dosya, asdict(r))}")
        elif args.komut == "staging":
            parola = os.environ.get("STAGING_YONETICI_PAROLA")
            if not parola:
                print("STAGING_YONETICI_PAROLA ortam değişkeni gerekli.", file=sys.stderr)
                return 2
            r = await tenant_geri_yukle(db_url, Path(args.dosya), args.hedef)
            a = await tenant_anonimlestir(
                asyncpg_dsn(db_url), args.hedef, yonetici=(args.yonetici_eposta, parola)
            )
            _yaz({"islem": "staging", "geri_yukleme": asdict(r), "anonim": asdict(a)})
    except YedekHatasi as exc:
        _yaz({"islem": args.komut, "hata": str(exc)})
        return 1
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="FabrikaOS tenant yedek aracı")
    alt = p.add_subparsers(dest="komut", required=True)
    a = alt.add_parser("al", help="tek tenant yedeği")
    a.add_argument("slug")
    a.add_argument("--dizin", required=True)
    t = alt.add_parser("tumu", help="tüm aktif tenant'ların yedeği")
    t.add_argument("--dizin", required=True)
    d = alt.add_parser("dogrula", help="yedek dosyasının bütünlüğünü denetle")
    d.add_argument("dosya")
    g = alt.add_parser("geri-yukle", help="yedeği geri yükle (canlı şemayla yer değiştirir)")
    g.add_argument("dosya")
    g.add_argument("--hedef", default=None, help="hedef slug (varsayılan: yedeğin slug'ı)")
    g.add_argument("--evet", action="store_true")
    k = alt.add_parser("tatbikat", help="yedek al + geçici şemaya geri yükle + doğrula + raporla")
    k.add_argument("slug")
    k.add_argument("--dizin", required=True)
    k.add_argument("--rapor", default=None, help="tatbikat raporu dizini (markdown)")
    s = alt.add_parser("staging", help="yedeği staging tenant'ına yükle ve anonimleştir")
    s.add_argument("dosya")
    s.add_argument("--hedef", required=True, help="adında 'staging' geçen hedef slug")
    s.add_argument("--yonetici-eposta", required=True)
    args = p.parse_args()
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    return asyncio.run(_ana(args))


if __name__ == "__main__":
    sys.exit(main())
