"""`tur='duzeltme'` (MUTLAK yazım) hareketlerini tüm tenant'larda tarar.

Bu tür bakiyeyi mutlak yazar; hazırlanma ile uygulanma arasında yapılan hareketleri
sessizce siler (ADR-0024, REFACTOR-BACKLOG #2). Betik, **geçmişte kullanılıp
kullanılmadığını** ve hangi tenant/malzemelerin etkilenmiş olabileceğini raporlar.

"Şüpheli" tanımı: bir düzeltme hareketinin **kendisinden önceki hareketin
``bakiye_sonrasi``'sı ile aynı olmaması** tek başına anormal değildir (düzeltmenin amacı
budur). Asıl risk, düzeltme ile **aynı gün içinde ondan önce başka hareket olması**dır:
o hareketler mutlak yazımla ezilmiş olabilir.

Kullanım (repo kökünden):
    ./.venv/Scripts/python.exe backend/scripts/duzeltme_denetimi.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.control_plane.models import Tenant
from app.core.config import get_settings
from app.core.db.tenancy import sema_adi

SORGU = """
SELECT
    h.id,
    h.malzeme_id,
    m.kod  AS malzeme_kod,
    m.ad   AS malzeme_ad,
    h.miktar,
    h.bakiye_sonrasi,
    h.olusturma_tarihi,
    h.olusturan_kullanici_id,
    (
        SELECT count(*)
        FROM "{sema}".stok_hareketleri o
        WHERE o.malzeme_id = h.malzeme_id
          AND o.olusturma_tarihi < h.olusturma_tarihi
          AND o.olusturma_tarihi >= h.olusturma_tarihi - interval '1 day'
    ) AS onceki_24s_hareket
FROM "{sema}".stok_hareketleri h
JOIN "{sema}".malzemeler m ON m.id = h.malzeme_id
WHERE h.tur = 'duzeltme'
ORDER BY h.olusturma_tarihi DESC
"""


async def main() -> int:
    engine = create_async_engine(get_settings().database_url, poolclass=NullPool)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    toplam = 0
    supheli_toplam = 0
    try:
        async with sm() as s:
            tenantlar = [t.slug for t in (await s.execute(select(Tenant))).scalars()]

        for slug in tenantlar:
            sema = sema_adi(slug)
            async with sm() as s:
                try:
                    satirlar = (await s.execute(text(SORGU.format(sema=sema)))).mappings().all()
                except Exception as exc:  # noqa: BLE001 — yarım şema taramayı durdurmasın
                    print(f"  {slug}: OKUNAMADI ({type(exc).__name__})")
                    continue

            if not satirlar:
                print(f"  {slug}: temiz (mutlak düzeltme hareketi yok)")
                continue

            supheli = [r for r in satirlar if r["onceki_24s_hareket"] > 0]
            toplam += len(satirlar)
            supheli_toplam += len(supheli)
            print(f"  {slug}: {len(satirlar)} düzeltme hareketi, {len(supheli)} ŞÜPHELİ")
            for r in supheli[:10]:
                print(
                    f"      #{r['id']} malzeme={r['malzeme_kod']} ({r['malzeme_ad']}) "
                    f"miktar={r['miktar']} bakiye_sonrasi={r['bakiye_sonrasi']} "
                    f"tarih={r['olusturma_tarihi']:%Y-%m-%d %H:%M} "
                    f"onceki_24s_hareket={r['onceki_24s_hareket']}"
                )
            if len(supheli) > 10:
                print(f"      … ve {len(supheli) - 10} kayıt daha")
    finally:
        await engine.dispose()

    print()
    if toplam == 0:
        print("SONUC: hicbir tenant'ta mutlak duzeltme hareketi KULLANILMAMIS — veri riski yok.")
        return 0
    print(f"SONUC: toplam {toplam} duzeltme hareketi, {supheli_toplam} tanesi supheli.")
    print("Supheli kayitlar icin ilgili malzemenin fiziksel sayimla dogrulanmasi onerilir.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
