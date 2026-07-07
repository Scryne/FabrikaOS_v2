"""Analitik saf hesaplar — dönem/gün toplamlarından OEE ve fire oranı.

S3 ``oee_hesapla`` yeniden kullanılır: toplulaştırılmış satırlarda ideal çevrim makine
başına değiştiği için **adet-ağırlıklı ortalama çevrim** (``ideal_toplam_sn / toplam_adet``)
verilir; ``ideal_sure = ortalama_cevrim × toplam_adet`` matematiği satır-bazlı toplamla
birebir aynı sonuca ulaşır.
"""

from __future__ import annotations

from app.modules.uretim.oee import OeeSonuc, oee_hesapla


def donem_oee(
    *,
    planlanan_sure_dk: float,
    durus_sure_dk: float,
    toplam_adet: int,
    saglam_adet: int,
    ideal_toplam_sn: float,
) -> OeeSonuc:
    """Toplam bileşenlerden dönem (veya gün) OEE'si."""
    ortalama_cevrim = ideal_toplam_sn / toplam_adet if toplam_adet > 0 else 0.0
    return oee_hesapla(
        planlanan_sure_dk=planlanan_sure_dk,
        durus_sure_dk=durus_sure_dk,
        toplam_adet=toplam_adet,
        saglam_adet=saglam_adet,
        ideal_cevrim_sn=ortalama_cevrim,
    )


def fire_orani(toplam_adet: int, saglam_adet: int) -> float:
    """Fire oranı = (toplam − sağlam) / toplam; üretim yoksa 0."""
    return (toplam_adet - saglam_adet) / toplam_adet if toplam_adet > 0 else 0.0
