# Değişiklik günlüğü

Biçim: [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/). Sürüm numaraları
[SemVer](https://semver.org/lang/tr/)'e uyar. `v1.0.0` (GA) pilot müşteri kabulünden (UAT) sonra
etiketlenir (ADR-0043); o güne kadar her şey **Yayımlanmamış** başlığındadır. Ayrıntılı kararlar
ADR'lerde, sprint kabul kriterleri `docs/yol-haritasi.md`'de.

## Yayımlanmamış

### Faz 5 — Operasyon
- **S22 sertleştirme ve kapasite (ADR-0043):** CI'da bandit kapısı; NFR-01 k6 senaryosu
  (`perf/k6/`); API varsayılan 4 işçi (50 kullanıcıda p95 154 ms); Prometheus çok süreç modu.
- **S21 kurulum ve içe aktarma (ADR-0042):** `scripts/kurulum.py`; Yönetim › Veri içe aktarma
  (firma, makine, malzeme, personel, açılış stoğu; önizle → hepsi ya da hiçbiri).
- **S20 yedekleme/DR (ADR-0041):** tenant-farkında yedek/geri yükleme, PITR runbook'u, anonim
  staging kopyası, tenant başına göç dağıtımı, prod compose katmanı (Traefik joker TLS).
- **S19 gözlemlenebilirlik (ADR-0040):** `/metrics`, Sentry, OpenTelemetry, gerçek hazırlık
  yoklaması, SLO yanma hızı alarmları, Grafana panosu.

### Faz 6 — Kurumsal derinleşme
- **S25 tedarik zinciri (ADR-0024):** depo/lokasyon/lot, transfer, delta sayım, satınalma
  siparişi → kısmi teslim → iade, hızlı mal kabul eşleşmesi, etiket PDF.
- **S24 üretim ve bakım (ADR-0023):** vardiya, duruş, ürün/reçete (BOM), lot izlenebilirliği,
  MTBF/MTTR.
- **S23 güvenlik ve uyum (ADR-0022):** TOTP 2FA, SSO (OIDC), denetim kaydı görüntüleyici, KVKK
  self-servis ihraç.

### Faz 4/4B — Lisanslama, entegrasyon, vitrin bütünlüğü
- **S-VB (ADR-0021):** bildirim merkezi, SLA, tedarikçi skoru, coğrafi harita, takvim.
- **S18 (ADR-0020):** dış portal, imzalı webhook'lar, API anahtarları.
- **S17 (ADR-0019):** platform yönetici paneli, tenant yaşam döngüsü, KVKK tenant ihracı.
- **S16 (ADR-0018):** abonelik planları, modül hakları, özellik bayrakları, koltuk sınırı.

### Faz 3 — Zekâ
- **S15 (ADR-0017):** dijital ikiz ve kiosk. **S14 (ADR-0016):** analitik ve rapor (PDF/XLSX).
- **S13 (ADR-0015):** AI çekirdeği (kestirimci bakım, anomali, OEE, stok tahmini).

### Faz 2 — Saha ve modüller
- **S12 (ADR-0014):** CRM, sözleşme, talep, DYS, duyuru. **S11 (ADR-0013):** İSG ve İK.
- **S10 (ADR-0012):** kalite (CAPA) ve enerji (hypertable + sürekli toplulaştırma).
- **S9 (ADR-0011):** stok ve satınalma. **S8 (ADR-0010):** edge cihaz + MQTT ingestion.

### Faz 0–1 — Temel ve MVP
- Çok kiracılılık (şema başına tenant, ADR-0003), OAuth2/JWT + RBAC (ADR-0005), Alembic fan-out
  (ADR-0004), üretim/OEE (ADR-0006), iş emri durum makinesi + outbox (ADR-0007), SPA (ADR-0008),
  gerçek zaman (ADR-0009).
