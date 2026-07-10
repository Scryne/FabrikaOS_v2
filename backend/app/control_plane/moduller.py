"""Modül, özellik ve plan katalogları (control-plane; S16 / ADR-0018).

Kaynak gerçeği bu dosyadır: ``planlar`` tablosu migration'da bu katalogdan seed edilir
ve provizyonlama her koşuda upsert ile eşitler. Yeni modül eklendikçe ``MODUL_KATALOGU``
büyür; kimlik/kullanıcı/rol/abonelik uçları **çekirdektir** ve entitlement dışıdır.

Satılabilir birim = modül. İkiz+kiosk ``uretim``'e, ticari pano ``crm``'e, satınalma
``stok``'a bağlıdır (menü bölümleriyle hizalı; ayrı satılmaz).
"""

from __future__ import annotations

from dataclasses import dataclass

# kod -> insan-okur ad (i18n arayüzde; burada TR referans etiketi).
MODUL_KATALOGU: dict[str, str] = {
    "uretim": "Üretim & OEE (makineler, üretim verileri, dijital ikiz, kiosk)",
    "saha": "Saha & Edge (cihazlar, ölçüm toplama)",
    "isemri": "İş Emirleri",
    "bakim": "Bakım Planları",
    "stok": "Stok & Satınalma (malzeme, hareket, talep/onay)",
    "kalite": "Kalite (denetim, uygunsuzluk/CAPA)",
    "enerji": "Enerji İzleme",
    "isg": "İSG (kaza, risk değerlendirme)",
    "ik": "İK (personel, izin, mesai, zimmet, sertifika)",
    "crm": "CRM (firma/ortak, ticari pano)",
    "sozlesme": "Sözleşmeler",
    "talep": "Talepler",
    "dys": "Doküman Yönetimi",
    "duyuru": "Duyurular",
    "ai": "AI Tahminleri",
    "analitik": "Analitik",
    "rapor": "Raporlama",
    # S18 üst-segment eklentileri: yalnız deneme/kurumsal planlarında.
    "entegrasyon": "Entegrasyon (webhook, API anahtarları)",
    "dis-portal": "Dış Portal (müşteri self-servis)",
}


@dataclass(frozen=True)
class OzellikTanim:
    """Bir özellik bayrağının katalog tanımı."""

    ad: str
    deneysel: bool = False


# Özellik bayrakları: modül değil, kesitsel/erken-erişim anahtarları.
# `webhook-onizleme` S18'de tüketilir: webhook uçları `entegrasyon` modülü VEYA bu
# bayrak açıksa erişilir (modülü satın almamış tenant'a ön izleme). `mobil-api` → FAZ 7.
OZELLIK_KATALOGU: dict[str, OzellikTanim] = {
    "mobil-api": OzellikTanim(ad="Mobil Saha API'si (ön izleme)", deneysel=True),
    "webhook-onizleme": OzellikTanim(ad="Webhook entegrasyonu (ön izleme)", deneysel=True),
}


@dataclass(frozen=True)
class PlanTanim:
    """Bir satış planının katalog tanımı (``koltuk_limiti=None`` = sınırsız)."""

    kod: str
    ad: str
    koltuk_limiti: int | None
    moduller: frozenset[str]
    ozellikler: frozenset[str]


_TUM_MODULLER = frozenset(MODUL_KATALOGU)
_TUM_OZELLIKLER = frozenset(OZELLIK_KATALOGU)
_TEMEL_MODULLER = frozenset({"uretim", "isemri", "bakim", "stok"})
_PROFESYONEL_MODULLER = _TEMEL_MODULLER | frozenset(
    {"saha", "kalite", "enerji", "isg", "ik", "crm", "sozlesme", "talep", "dys", "duyuru"}
)

PLAN_KATALOGU: dict[str, PlanTanim] = {
    "deneme": PlanTanim(
        kod="deneme",
        ad="Deneme",
        koltuk_limiti=5,
        moduller=_TUM_MODULLER,
        ozellikler=_TUM_OZELLIKLER,
    ),
    "temel": PlanTanim(
        kod="temel",
        ad="Temel",
        koltuk_limiti=10,
        moduller=_TEMEL_MODULLER,
        ozellikler=frozenset(),
    ),
    "profesyonel": PlanTanim(
        kod="profesyonel",
        ad="Profesyonel",
        koltuk_limiti=50,
        moduller=_PROFESYONEL_MODULLER,
        ozellikler=frozenset(),
    ),
    "kurumsal": PlanTanim(
        kod="kurumsal",
        ad="Kurumsal",
        koltuk_limiti=None,
        moduller=_TUM_MODULLER,
        ozellikler=_TUM_OZELLIKLER,
    ),
}
