"""İzin/rol kataloğunu tüm tenant şemalarıyla uzlaştırır (idempotent).

Normalde **gerekmez**: `tenant_yukselt_tum` (migration fan-out) bunu kendiliğinden koşar.
Bu betik elle doğrulama/onarım içindir — ör. fan-out'un uzlaştırma adımı bir dağıtımda
atlanmışsa ya da bir tenant o sırada hata verdiyse.

Kullanım (repo kökünden):
    ./.venv/Scripts/python.exe backend/scripts/izin_uzlastir.py
    ./.venv/Scripts/python.exe backend/scripts/izin_uzlastir.py --kuru   # yalnız rapor
"""

from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.control_plane.models import Tenant
from app.control_plane.uzlastirma import izin_rol_uzlastir, tum_tenantlari_uzlastir
from app.core.config import get_settings
from app.core.db.tenancy import search_path_ayarla
from app.kimlik.izinler import IZIN_KATALOGU
from app.kimlik.models import Izin


async def _kuru_rapor() -> int:
    """Hiçbir şey yazmadan eksikleri raporlar; eksik varsa çıkış kodu 1."""
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    eksik_toplam = 0
    try:
        async with sm() as s:
            sluglar = [t.slug for t in (await s.execute(select(Tenant))).scalars()]
        for slug in sluglar:
            async with sm() as s:
                await search_path_ayarla(s, slug)
                mevcut = {i.kod for i in (await s.execute(select(Izin))).scalars()}
            eksik = sorted(set(IZIN_KATALOGU) - mevcut)
            if eksik:
                eksik_toplam += len(eksik)
                print(f"  {slug}: {len(eksik)} eksik izin -> {', '.join(eksik)}")
            else:
                print(f"  {slug}: tam")
    finally:
        await engine.dispose()
    return eksik_toplam


async def _uygula() -> None:
    sonuclar = await tum_tenantlari_uzlastir()
    for s in sonuclar:
        if s.degisti:
            print(
                f"  {s.slug}: +{len(s.eklenen_izin)} izin, +{len(s.eklenen_rol)} rol, "
                f"~{len(s.guncellenen_rol)} rol guncellendi"
            )
        else:
            print(f"  {s.slug}: degisiklik yok")


def main() -> int:
    ayristirici = argparse.ArgumentParser(description=__doc__)
    ayristirici.add_argument("--kuru", action="store_true", help="Yalnız raporla, değişiklik yazma")
    argumanlar = ayristirici.parse_args()

    print(f"Katalogdaki izin sayisi: {len(IZIN_KATALOGU)}")
    if argumanlar.kuru:
        eksik = asyncio.run(_kuru_rapor())
        print("SONUC: eksik yok" if eksik == 0 else f"SONUC: toplam {eksik} eksik izin")
        return 1 if eksik else 0
    asyncio.run(_uygula())
    print("SONUC: uzlastirma tamam")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# İzin_rol_uzlastir doğrudan da kullanılabilir (tek tenant onarımı).
__all__ = ["izin_rol_uzlastir", "main"]
