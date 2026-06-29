"""OEE (Overall Equipment Effectiveness) saf hesaplama fonksiyonu.

OEE = Kullanılabilirlik × Performans × Kalite

- **Kullanılabilirlik** = çalışma süresi / planlanan süre
  (çalışma süresi = planlanan − duruş; negatifse 0).
- **Performans** = ideal üretim süresi / çalışma süresi
  (ideal süre = ideal çevrim × toplam adet); 1.0 ile sınırlıdır.
- **Kalite** = sağlam adet / toplam adet.

Saf fonksiyon: DB/IO yoktur, deterministiktir → kapsamlı birim testlerle güvencelenir.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OeeSonuc:
    kullanilabilirlik: float
    performans: float
    kalite: float
    oee: float


def oee_hesapla(
    *,
    planlanan_sure_dk: float,
    durus_sure_dk: float,
    toplam_adet: int,
    saglam_adet: int,
    ideal_cevrim_sn: float,
) -> OeeSonuc:
    """OEE bileşenlerini ve toplamını hesaplar. Geçersiz girdide ``ValueError``."""
    if min(planlanan_sure_dk, durus_sure_dk, toplam_adet, saglam_adet, ideal_cevrim_sn) < 0:
        raise ValueError("OEE girdileri negatif olamaz")
    if saglam_adet > toplam_adet:
        raise ValueError("Sağlam adet toplam adetten büyük olamaz")

    calisma_dk = max(planlanan_sure_dk - durus_sure_dk, 0.0)

    kullanilabilirlik = calisma_dk / planlanan_sure_dk if planlanan_sure_dk > 0 else 0.0

    ideal_sure_dk = ideal_cevrim_sn * toplam_adet / 60.0
    performans = min(ideal_sure_dk / calisma_dk, 1.0) if calisma_dk > 0 else 0.0

    kalite = saglam_adet / toplam_adet if toplam_adet > 0 else 0.0

    oee = kullanilabilirlik * performans * kalite
    return OeeSonuc(
        kullanilabilirlik=kullanilabilirlik,
        performans=performans,
        kalite=kalite,
        oee=oee,
    )
