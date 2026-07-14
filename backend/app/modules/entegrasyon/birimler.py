"""Entegrasyon domain sabitleri — webhook olay türü kataloğu + API anahtar kapsamları.

``OLAY_TURU_KATALOGU`` anahtarları üretici modüllerdeki ``olay_yayinla`` sabitleriyle
birebir aynı string'lerdir (tek doğruluk kaynağı üreticidir; katalog aboneliklerin
seçebileceği türleri ve FE çiplerini besler).
"""

from __future__ import annotations

# kod -> insan-okur açıklama (TR referans; FE i18n kendi etiketini taşır).
OLAY_TURU_KATALOGU: dict[str, str] = {
    "is_emri.kapandi": "İş emri kapandı",
    "ariza.olustu": "Arıza kaydı oluştu",
    "stok.kritik": "Stok kritik eşiğin altına indi",
    "oee.dustu": "Makine OEE'si hedefin altına düştü",
    "sozlesme.yaklasiyor": "Sözleşme bitişi yaklaşıyor",
    "anomali.tespit": "AI anomali tespiti",
    "kalite.uygunsuzluk": "Kalite uygunsuzluğu açıldı",
    "isg.kaza": "İş kazası kaydı oluştu",
    "sla.asildi": "SLA hedef tarihi aşıldı",
}

# API anahtarı kapsam beyaz-listesi: dış veri uçlarının istediği okuma izinleri.
# Anahtara ancak bu alt kümeden kapsam atanabilir (en az ayrıcalık).
ENTEGRASYON_IZIN_KAPSAMLARI: dict[str, str] = {
    "uretim:oku": "Üretim özeti okuma",
    "stok:oku": "Stok bakiyeleri okuma",
    "satinalma:oku": "Satınalma talepleri okuma",
}
