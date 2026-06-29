"""Üretim modülü iş kuralları — OEE toplulaştırma.

Toplulaştırılmış girdiler (``OeeToplam``) saf ``oee_hesapla`` fonksiyonuna bağlanır:
toplam ideal süreden "efektif çevrim süresi" türetilerek tek doğruluk kaynağı korunur.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.uretim import repository
from app.modules.uretim.oee import OeeSonuc, oee_hesapla
from app.modules.uretim.repository import OeeToplam


def oee_toplamdan(t: OeeToplam) -> OeeSonuc:
    """Toplulaştırılmış girdilerden OEE hesaplar (saf fonksiyonu yeniden kullanır)."""
    # ideal_sure_dk = efektif_cevrim_sn * toplam_adet / 60  →  efektif_cevrim_sn'i geri çöz.
    efektif_cevrim_sn = t.ideal_sure_dk * 60.0 / t.toplam_adet if t.toplam_adet > 0 else 0.0
    return oee_hesapla(
        planlanan_sure_dk=t.planlanan_sure_dk,
        durus_sure_dk=t.durus_sure_dk,
        toplam_adet=t.toplam_adet,
        saglam_adet=t.saglam_adet,
        ideal_cevrim_sn=efektif_cevrim_sn,
    )


async def makine_oee(
    db: AsyncSession,
    makine_id: int,
    *,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
) -> tuple[OeeSonuc, int]:
    toplam = await repository.oee_toplam(db, makine_id, baslangic=baslangic, bitis=bitis)
    return oee_toplamdan(toplam), toplam.kayit_sayisi


async def oee_ozet(
    db: AsyncSession,
    *,
    baslangic: datetime | None = None,
    bitis: datetime | None = None,
) -> list[tuple[int, str, OeeSonuc, int]]:
    satirlar = await repository.oee_ozet(db, baslangic=baslangic, bitis=bitis)
    return [(mid, kod, oee_toplamdan(t), t.kayit_sayisi) for mid, kod, t in satirlar]
