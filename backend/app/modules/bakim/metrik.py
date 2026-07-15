"""MTBF / MTTR hesabı — saf (DB'siz) fonksiyon, bilinen seriyle birim testli (S24).

Girdiler pencere içindeki arıza kayıtlarıdır (başlangıç, bitiş|None):

- **MTTR** (Mean Time To Repair) = kapanmış arızaların toplam onarım süresi / kapanmış
  arıza sayısı (saat). Açık arızalar MTTR'a girmez (onarım süresi henüz bilinmiyor).
- **MTBF** (Mean Time Between Failures) = (pencere süresi − toplam arıza süresi) /
  arıza sayısı (saat). Açık arızanın süresi pencere sonuna kadar sayılır.

Arıza yoksa iki metrik de ``None`` döner (sıfıra bölme imkânsız; "arıza yok" ≠ "MTBF 0").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class MtbfMttr:
    ariza_sayisi: int
    kapanan_ariza: int
    toplam_ariza_saat: float
    mtbf_saat: float | None
    mttr_saat: float | None


def mtbf_mttr_hesapla(
    arizalar: list[tuple[datetime, datetime | None]],
    *,
    pencere_baslangic: datetime,
    pencere_bitis: datetime,
) -> MtbfMttr:
    """Pencere içi arıza listesinden MTBF/MTTR üretir (saat cinsinden, deterministik)."""
    pencere_saat = max((pencere_bitis - pencere_baslangic).total_seconds() / 3600.0, 0.0)
    ariza_sayisi = len(arizalar)
    if ariza_sayisi == 0:
        return MtbfMttr(
            ariza_sayisi=0, kapanan_ariza=0, toplam_ariza_saat=0.0, mtbf_saat=None, mttr_saat=None
        )

    toplam_ariza_saat = 0.0
    onarim_toplam_saat = 0.0
    kapanan = 0
    for baslangic, bitis in arizalar:
        bas = max(baslangic, pencere_baslangic)
        bit = min(bitis or pencere_bitis, pencere_bitis)
        sure = max((bit - bas).total_seconds() / 3600.0, 0.0)
        toplam_ariza_saat += sure
        if bitis is not None:
            kapanan += 1
            onarim_toplam_saat += max((bitis - baslangic).total_seconds() / 3600.0, 0.0)

    calisma_saat = max(pencere_saat - toplam_ariza_saat, 0.0)
    return MtbfMttr(
        ariza_sayisi=ariza_sayisi,
        kapanan_ariza=kapanan,
        toplam_ariza_saat=round(toplam_ariza_saat, 2),
        mtbf_saat=round(calisma_saat / ariza_sayisi, 2),
        mttr_saat=round(onarim_toplam_saat / kapanan, 2) if kapanan > 0 else None,
    )
