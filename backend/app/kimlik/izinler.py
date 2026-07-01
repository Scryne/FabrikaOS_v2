"""RBAC izin kataloğu ve varsayılan roller (tohum verisi kaynağı).

İzin kodu biçimi ``modul:islem`` (Türkçe-ASCII). Yeni modül eklendikçe katalog büyür;
provizyonlama tohumu (``provizyon.py``) bu katalogdan tenant şemasına izin/rol yazar.
``platform-admin`` control-plane'e aittir; tenant kataloğunda yer almaz.
"""

from __future__ import annotations

# (kod, açıklama) — plan §3.3 ile uyumlu çekirdek izinler.
IZIN_KATALOGU: dict[str, str] = {
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
    "enerji:oku": "Enerji tüketimini görüntüleme",
    "enerji:yaz": "Enerji tüketimi girişi",
    "crm:oku": "CRM kayıtlarını görüntüleme",
    "talep:yaz": "Talep oluşturma",
    "dys:oku": "Belgeleri görüntüleme",
    "dys:yaz": "Belge yükleme/güncelleme",
    "ai:oku": "AI tahminlerini görüntüleme",
    "analitik:oku": "Analitik panoları görüntüleme",
    "rapor:oku": "Raporları görüntüleme",
    "rapor:yaz": "Rapor oluşturma",
}

# Salt-okunur (izleyici) rolü için *:oku izinleri.
_OKU_IZINLERI = frozenset(k for k in IZIN_KATALOGU if k.endswith(":oku"))

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
}
