"""RBAC izin kataloğu ve varsayılan roller (tohum verisi kaynağı).

İzin kodu biçimi ``modul:islem`` (Türkçe-ASCII). Yeni modül eklendikçe katalog büyür;
provizyonlama tohumu (``provizyon.py``) bu katalogdan tenant şemasına izin/rol yazar.
``platform-admin`` control-plane'e aittir; tenant kataloğunda yer almaz.
"""

from __future__ import annotations

# (kod, açıklama) — plan §3.3 ile uyumlu çekirdek izinler.
IZIN_KATALOGU: dict[str, str] = {
    "abonelik:oku": "Abonelik ve modül durumunu görüntüleme",
    "kullanici:oku": "Kullanıcıları görüntüleme",
    "kullanici:yaz": "Kullanıcı oluşturma/güncelleme",
    "kullanici:sil": "Kullanıcı silme",
    "rol:oku": "Rolleri görüntüleme",
    "rol:yaz": "Rol/izin atama",
    "uretim:oku": "Üretim verilerini görüntüleme",
    "uretim:yaz": "Üretim verisi girişi",
    "saha:oku": "Saha cihazlarını görüntüleme",
    "saha:yaz": "Saha cihazı oluşturma/güncelleme",
    "edge": "Saha ölçümü gönderme (edge ingestion)",
    "isemri:oku": "İş emirlerini görüntüleme",
    "isemri:yaz": "İş emri oluşturma/güncelleme",
    "bakim:oku": "Bakım planlarını görüntüleme",
    "bakim:yaz": "Bakım planı oluşturma/güncelleme",
    "stok:oku": "Stok görüntüleme",
    "stok:yaz": "Stok hareketi girişi",
    "satinalma:oku": "Satınalma taleplerini görüntüleme",
    "satinalma:yaz": "Satınalma talebi oluşturma",
    "satinalma:onay": "Satınalma talebini onaylama",
    "kalite:oku": "Kalite kayıtlarını görüntüleme",
    "kalite:yaz": "Kalite kaydı girişi",
    "isg:oku": "İSG kayıtlarını görüntüleme",
    "isg:yaz": "İSG kaydı girişi",
    "ik:oku": "İK kayıtlarını görüntüleme",
    "ik:yaz": "İK kaydı girişi",
    "ik:onay": "İzin talebini onaylama",
    "enerji:oku": "Enerji tüketimini görüntüleme",
    "enerji:yaz": "Enerji tüketimi girişi",
    "crm:oku": "CRM (firma/ortak) kayıtlarını görüntüleme",
    "crm:yaz": "CRM (firma/ortak) kaydı girişi",
    "sozlesme:oku": "Sözleşmeleri görüntüleme",
    "sozlesme:yaz": "Sözleşme oluşturma/güncelleme",
    "talep:oku": "Talepleri görüntüleme",
    "talep:yaz": "Talep oluşturma/güncelleme",
    "dys:oku": "Belgeleri görüntüleme",
    "dys:yaz": "Belge yükleme/güncelleme",
    "duyuru:oku": "Duyuruları görüntüleme",
    "duyuru:yaz": "Duyuru oluşturma/yayınlama",
    "ai:oku": "AI tahminlerini görüntüleme",
    "ai:egit": "AI modeli eğitimini başlatma",
    "analitik:oku": "Analitik panoları görüntüleme",
    "rapor:oku": "Raporları görüntüleme",
    "rapor:yaz": "Rapor oluşturma",
    "entegrasyon:oku": "Webhook aboneliklerini ve API anahtarlarını görüntüleme",
    "entegrasyon:yaz": "Webhook aboneliği ve API anahtarı yönetimi",
    "dis:erisim": "Dış self-servis portal erişimi (firma-kapsamlı)",
    # S23 (ADR-0022) — güvenlik & uyum çekirdek yüzeyi (modül kapısı YOK: satılabilir
    # yetenek değil, her tenant'ın hakkı; yalnız izinle korunur).
    "denetim:oku": "Denetim kayıtlarını (audit trail) görüntüleme",
    "kvkk:yonet": "KVKK ihracı ve anonimleştirme yönetimi",
}

# Salt-okunur (izleyici) rolü için *:oku izinleri. Denetim kaydı hariç: adli iz
# hassas kişisel veri içerir, geniş izleyici rolüne otomatik verilmez (S23).
_OKU_IZINLERI = frozenset(k for k in IZIN_KATALOGU if k.endswith(":oku")) - {"denetim:oku"}

# Varsayılan roller: ad -> izin kodları kümesi. "admin" tüm kataloğa sahiptir.
VARSAYILAN_ROLLER: dict[str, frozenset[str]] = {
    "admin": frozenset(IZIN_KATALOGU.keys()),
    "izleyici": _OKU_IZINLERI,
    # Saha/cihaz servis hesapları (REST/MQTT ingestion için yalnız edge izni).
    "saha-cihaz": frozenset({"edge"}),
    # Depo sorumlusu: stok + talep oluşturur, ONAYLAYAMAZ (görev ayrımı).
    "depo": frozenset({"stok:oku", "stok:yaz", "satinalma:oku", "satinalma:yaz"}),
    # Satınalma onaylayan: yalnız talep görüntüleme + onay.
    "satinalma-onaylayan": frozenset({"satinalma:oku", "satinalma:onay"}),
    # Kalite sorumlusu: denetim + uygunsuzluk/CAPA yönetir.
    "kalite": frozenset({"kalite:oku", "kalite:yaz"}),
    # Enerji sorumlusu: tüketim görüntüler + girer.
    "enerji": frozenset({"enerji:oku", "enerji:yaz"}),
    # İSG uzmanı: kaza + risk değerlendirme girer/görüntüler.
    "isg": frozenset({"isg:oku", "isg:yaz"}),
    # İK sorumlusu: personel/izin girer, izin ONAYLAYAMAZ (görev ayrımı).
    "ik": frozenset({"ik:oku", "ik:yaz"}),
    # İK onaylayan (yönetici): personel görüntüler + izin talebini onaylar/reddeder.
    "ik-onaylayan": frozenset({"ik:oku", "ik:onay"}),
    # CRM/satış sorumlusu: firma/ortak + sözleşme + talep yönetir.
    "crm": frozenset(
        {
            "crm:oku",
            "crm:yaz",
            "sozlesme:oku",
            "sozlesme:yaz",
            "talep:oku",
            "talep:yaz",
        }
    ),
    # Doküman sorumlusu: DYS belge/sürüm yükler + görüntüler.
    "dokuman": frozenset({"dys:oku", "dys:yaz"}),
    # Duyuru sorumlusu: duyuru oluşturur + yayınlar.
    "duyuru": frozenset({"duyuru:oku", "duyuru:yaz"}),
    # AI sorumlusu: tahminleri görüntüler + model eğitimi başlatır.
    "ai": frozenset({"ai:oku", "ai:egit"}),
    # Analist: KPI panolarını görüntüler + rapor oluşturur (izleyici yalnız okur).
    "analist": frozenset({"analitik:oku", "rapor:oku", "rapor:yaz"}),
    # Kiosk (büyük ekran): yalnız üretim/ikiz görünümü okur — salt-okunurluk API
    # seviyesinde garanti (en az ayrıcalık; S15/ADR-0017).
    "kiosk": frozenset({"uretim:oku"}),
    # Entegrasyon sorumlusu: webhook aboneliği + API anahtarı yönetir (S18).
    "entegrasyon": frozenset({"entegrasyon:oku", "entegrasyon:yaz"}),
    # Dış portal (müşteri/tedarikçi) kullanıcısı: YALNIZ /dis/* yüzeyi — iç modül
    # izinleriyle karışmaz (tenant-rbac-conventions); firma bağlantısı zorunlu.
    "dis-panel": frozenset({"dis:erisim"}),
    # Uyum sorumlusu (S23): denetim izi + KVKK ihraç/anonimleştirme yönetir.
    "uyum": frozenset({"denetim:oku", "kvkk:yonet"}),
}
