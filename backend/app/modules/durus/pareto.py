"""Duruş pareto analizi — saf hesap (DB'siz, birim testli).

Neden bazında toplam dakika azalan sırada; her satır yüzde + kümülatif yüzde taşır
(80/20 okuması). Toplam sıfırsa boş liste döner (bölme hatası imkânsız).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ParetoSatiri:
    neden: str
    sinif: str
    toplam_dk: float
    yuzde: float
    kumulatif_yuzde: float


def pareto_hesapla(girdiler: list[tuple[str, str, float]]) -> list[ParetoSatiri]:
    """(neden, sınıf, toplam_dk) listesinden sıralı pareto satırları üretir.

    Deterministik: dakika eşitliğinde ada göre alfabetik ikincil sıralama.
    """
    toplam = sum(dk for _, _, dk in girdiler)
    if toplam <= 0:
        return []
    sirali = sorted(girdiler, key=lambda g: (-g[2], g[0]))
    satirlar: list[ParetoSatiri] = []
    kumulatif = 0.0
    for neden, sinif, dk in sirali:
        yuzde = 100.0 * dk / toplam
        kumulatif += yuzde
        satirlar.append(
            ParetoSatiri(
                neden=neden,
                sinif=sinif,
                toplam_dk=round(dk, 1),
                yuzde=round(yuzde, 1),
                kumulatif_yuzde=round(min(kumulatif, 100.0), 1),
            )
        )
    return satirlar
