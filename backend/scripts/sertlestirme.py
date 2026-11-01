"""Sertleştirme taraması (S28, ADR-0047): OpenAPI'den üretilen girdilerle tüm uçlarda 500 avı.

Schemathesis şemadaki her ucu sınır değerleri, bozuk tipler, NUL baytı, dev tamsayılar ve durum
geçişleriyle (stateful: oluştur → oku → güncelle → sil) dener; tek denetim ``not_a_server_error``:
istemci ne gönderirse göndersin sunucu 5xx dönmemeli. İlk koşu 88 uçta 500 buldu (bkz.
``docs/operasyon/sertlestirme.md``); hepsi kapandı, bu betik geri dönüşü yakalar.

Betik kendi kendine yeter: tek kullanımlık bir veritabanı kurar (``--db-url``'deki ad sıfırlanır),
bir tenant provizyonlar, API'yi aynı süreçte bellek içi nesne deposuyla açar, taramayı koşar ve
schemathesis'in çıkış kodunu döner. Kullanım (repo kökünden)::

    python backend/scripts/sertlestirme.py \\
        --db-url postgresql+asyncpg://postgres@127.0.0.1:55432/fabrikaos_sertlik \\
        --redis-url redis://127.0.0.1:56379/3

Hariç tutulanlar bilerek: ``/kimlik/`` (çıkış, parola, 2FA taramanın kendi oturumunu düşürür),
``/platform/`` (ayrı platform kimliği ister), ``/kullanicilar`` (admin'i pasifleştirebilir).
"""

from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
TENANT = {
    "slug": "sertlik",
    "ad": "Sertlik Tarama",
    "eposta": "admin@sertlik.test",
    "parola": "Sertlik1234!",
}
HARIC = "/kimlik/|/platform/|/kullanicilar"


async def _db_sifirla(db_url: str) -> None:
    import asyncpg

    sunucu, ad = db_url.replace("postgresql+asyncpg://", "postgresql://").rsplit("/", 1)
    if not ad.isidentifier():
        raise SystemExit(f"Geçersiz veritabanı adı: {ad!r}")
    baglanti = await asyncpg.connect(f"{sunucu}/postgres")
    try:
        await baglanti.execute(f"DROP DATABASE IF EXISTS {ad} WITH (FORCE)")
        await baglanti.execute(f"CREATE DATABASE {ad}")
    finally:
        await baglanti.close()


def _sunucu_baslat(port: int) -> tuple[object, threading.Thread]:
    import uvicorn

    from app.main import create_app
    from app.modules.dys import depolama

    # Nesne deposu bellekte: tarama MinIO'nun yokluğunu değil API'nin girdiye dayanıklılığını ölçer
    # (depo kesintisi ayrıca test_s28_dayaniklilik.py'de: 503).
    depolama.nesne_depo_ayarla(depolama.BellekNesneDepo())
    sunucu = uvicorn.Server(
        uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning")
    )
    fabrika = asyncio.SelectorEventLoop if sys.platform == "win32" else None
    is_parcacigi = threading.Thread(
        target=lambda: asyncio.run(sunucu.serve(), loop_factory=fabrika), daemon=True
    )
    is_parcacigi.start()
    return sunucu, is_parcacigi


def _token(port: int) -> str:
    import httpx

    taban = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            if httpx.get(f"{taban}/saglik", timeout=2).status_code == 200:
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    else:
        raise SystemExit("API ayağa kalkmadı")
    r = httpx.post(
        f"{taban}/api/v1/kimlik/token",
        data={"username": TENANT["eposta"], "password": TENANT["parola"]},
        headers={"X-Tenant": TENANT["slug"]},
    )
    r.raise_for_status()
    return str(r.json()["data"]["access_token"])


def main() -> int:
    p = argparse.ArgumentParser(description="FabrikaOS sertleştirme taraması (schemathesis)")
    p.add_argument("--db-url", default=os.environ.get("SERTLIK_DB_URL"), required=False)
    p.add_argument("--redis-url", default=os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/3"))
    p.add_argument("--port", type=int, default=18765)
    p.add_argument("--ornek", type=int, default=10, help="uç başına örnek sayısı")
    p.add_argument("--tohum", type=int, default=28)
    p.add_argument("--isci", type=int, default=4)
    p.add_argument("--rapor", help="JUnit XML raporu yolu")
    a = p.parse_args()
    if not a.db_url:
        p.error("--db-url ya da SERTLIK_DB_URL gerekli (bu veritabanı sıfırlanır)")

    os.environ["DATABASE_URL"] = a.db_url
    os.environ["REDIS_URL"] = a.redis_url
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)

    from app.control_plane.provizyon import tenant_provizyonla
    from app.core.db import fanout

    asyncio.run(_db_sifirla(a.db_url))
    fanout.public_yukselt(db_url=a.db_url)
    asyncio.run(
        tenant_provizyonla(
            slug=TENANT["slug"],
            ad=TENANT["ad"],
            admin_eposta=TENANT["eposta"],
            admin_parola=TENANT["parola"],
            plan_kodu="kurumsal",
            db_url=a.db_url,
        )
    )
    sunucu, is_parcacigi = _sunucu_baslat(a.port)
    try:
        token = _token(a.port)
        komut = [
            sys.executable,
            "-c",
            "from schemathesis.cli import schemathesis; schemathesis()",
            "run",
            f"http://127.0.0.1:{a.port}/openapi.json",
            "--exclude-path-regex",
            HARIC,
            "-c",
            "not_a_server_error",
            "-n",
            str(a.ornek),
            "-w",
            str(a.isci),
            "--seed",
            str(a.tohum),
            "--request-timeout",
            "40",
            "-H",
            f"Authorization: Bearer {token}",
            "-H",
            f"X-Tenant: {TENANT['slug']}",
        ]
        if a.rapor:
            komut += ["--report", "junit", "--report-junit-path", a.rapor]
        return subprocess.run(komut, env=dict(os.environ, PYTHONUTF8="1")).returncode
    finally:
        sunucu.should_exit = True  # type: ignore[attr-defined]
        is_parcacigi.join(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
