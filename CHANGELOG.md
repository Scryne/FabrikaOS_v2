# Değişiklik günlüğü

Biçim: [Keep a Changelog](https://keepachangelog.com/tr/1.1.0/). Sürüm numaraları
[SemVer](https://semver.org/lang/tr/)'e uyar. `v1.0.0` (GA) pilot müşteri kabulünden (UAT) sonra
etiketlenir (ADR-0043); o güne kadar her şey **Yayımlanmamış** başlığındadır. Ayrıntılı kararlar
ADR'lerde, sprint kabul kriterleri `docs/yol-haritasi.md`'de.

## Yayımlanmamış

<details><summary>Tüm commit'ler</summary>

<!-- surum-notlari:baslangic -->
_Commit geçmişinden üretildi (`pre-s25`'ten bu yana); elle düzenlemeyin._

#### Sprintler
- **S28** kurumsal güvence: mutasyon, sertleştirme taraması, dayanıklılık, alan şifrelemesi, doküman seti (ADR-0047) (`e0496d1`)
- **S27** platform deneyimi: onay kutusu, içerik araması, code-split, dışa aktarma, sipariş PDF'i, erişilebilirlik (ADR-0045, ADR-0046) (`993ff42`)
- **S26-B** İSG + İK kurumsal tamamlama (ADR-0044) (`ebfb27c`)
- **S26-A** kalite olgunluğu: kontrol planı + SPC, ölçüm cihazı + kalibrasyon (ADR-0025) (`3c7c950`)
- **S22** bandit kapısı, NFR-01 k6 ölçümü, çok işçili API ve Prometheus çok süreç modu (ADR-0043) (`30dfef5`)
- **S21** kurulum komutu + onboarding veri içe aktarma (ADR-0042) (`806a72a`)
- **S20** tenant-farkında yedek/geri yükleme, PITR, anonim staging, göç dağıtımı (ADR-0041) (`b7b4aff`)
- **S19** gözlemlenebilirlik — metrik, Sentry, OTel, SLO alarmları (ADR-0040) (`c88cdc7`)
- **S25-B** satınalma siparişi → kısmi teslim → iade, etiket, teslim skoru (ADR-0024) (`8dea855`)
- **S25-A** depo/lokasyon, lot bakiyesi, transfer ve sayım (ADR-0024) (`a5d763b`)

#### Yeni
- **demo,compose:** seed eksik modulleri tamamlar ve veriyi bugune getirir; bildirim + relay surecleri (`a5f9f57`)
- **kvkk:** ihrac artefaktina saklama suresi + indirme denetimi + otomatik imha (`d2650f1`)
- **sso:** ham claim log penceresi sureli + denetim izli; PKCE acikca testli (`d4269ef`)
- **uyum:** izin katalogu <-> tenant semalari uzlastirmasi (sessiz surukleme kapandi) (`b7b37be`)

#### Düzeltme
- **ui:** mobil kabuk ve sayfa tasmalari, bildirim satiri, grafik etiketleri (`df5d722`)
- **ai,bildirim:** anomali bildirim yagmuru ve bos baslik (`1e653da`)
- **api:** beklenmeyen 500 CORS + x-request-id ile doner; WS token loga yazilmaz (`3aa8b97`)
- **test:** KVKK ihrac testleri hermetik — CI'da MinIO yoktu, 5 test 07-30'dan beri kiriliyordu (`fa2ffe9`)
- **guvenlik:** mutlak duzeltme korumasi + search_path commit kancasi + geriye donuk kabul karari (`d82e3e8`)
- **s23:** inceleme duzeltmeleri — yetki restorasyonu, imha sirasi, saklama gerekcesi (`853ce63`)

#### Güvenlik
- vite, vitest/@vitest/mocker, launch-editor, source-map-js (gelistirme bagimliliklari) (`769bbe0`)

#### Doküman
- README ve DURUM 2026-09 olcumu, DESIGN.md spec'e, ekran goruntuleri (`eb3d6ee`)
- **s25:** ADR-0024 tasarim kararlari + duzeltme hareketi backlog girdisi (`da78b8b`)
- S23 sertlestirme eki + KVKK/finans saklama catismasi backlog girdisi (`40f91a3`)

#### Test
- veritabanı sunucusu ve adı tek kaynaktan (TEST_DATABASE_URL) (`313f414`)

#### CI
- yalnız doküman/not değişen commit'te koşmaz (paths-ignore) (`b53cb82`)

#### Bakım
- **deps,ci:** Vite 8, Vitest 5, ECharts 6.1, Playwright 1.63; CI Node 22 + bagimlilik taramasi (`5f01c48`)

#### Diğer
- react-router 6.30.6 -> 7.18.4 (GHSA-wrjc-x8rr-h8h6, GHSA-337j-9hxr-rhxg) (`a124a61`)
- denetim 2026-08-27: DURUM.md + birikmis calisma commit edildi (`3e02700`)

<!-- surum-notlari:bitis -->

</details>

### Faz 5 — Operasyon
- **S22 sertleştirme ve kapasite (ADR-0043):** CI'da bandit kapısı; NFR-01 k6 senaryosu
  (`perf/k6/`); API varsayılan 4 işçi (50 kullanıcıda p95 154 ms); Prometheus çok süreç modu.
- **S21 kurulum ve içe aktarma (ADR-0042):** `scripts/kurulum.py`; Yönetim › Veri içe aktarma
  (firma, makine, malzeme, personel, açılış stoğu; önizle → hepsi ya da hiçbiri).
- **S20 yedekleme/DR (ADR-0041):** tenant-farkında yedek/geri yükleme, PITR runbook'u, anonim
  staging kopyası, tenant başına göç dağıtımı, prod compose katmanı (Traefik joker TLS).
- **S19 gözlemlenebilirlik (ADR-0040):** `/metrics`, Sentry, OpenTelemetry, gerçek hazırlık
  yoklaması, SLO yanma hızı alarmları, Grafana panosu.

### Faz 7 — Kurumsal uygulama genişlemesi
- **S32 ESG & sürdürülebilirlik (ADR-0051):** yeni `esg` modülü — Kapsam 1/2 emisyon (kaynaklı varsayılan
  faktörler + tenant faktörü, tarihe göre), faktörsüz tüketim ayrı, karbon ve enerji yoğunluğu, ESG raporu;
  Sürdürülebilirlik ekranı.
- **S31 satış & sipariş → MRP (ADR-0050):** yeni `satis` modülü — müşteri siparişi, tek seviyeli BOM ile
  malzeme ihtiyacı (açık tedarik ve açık iş emri tüketimi hesaba katılarak), onayda üretim iş emri ve
  eksik malzeme için satınalma talebi (idempotent, görev ayrımlı); Satış siparişleri ekranı.
- **S30 üretim planlama (ADR-0049):** yeni `planlama` modülü — makine başına sonlu kapasiteli
  çizelge (vardiya pencereleri, EDD, devam eden önce), elle süre/sıra girdisi, kapasite aşımı ile
  sıra kaynaklı gecikmenin ayrımı, günlük yük; Üretim planı ekranı (Gantt + yük ızgarası + iş sırası).
- **S29 finans & muhasebe (ADR-0048):** yeni `finans` modülü — cari hesap (kilitli tutulan bakiye,
  çift sayımsız), satış/alış faturası (hazırla → onay → kes → kapandı; hazırlayan kesemez),
  tahsilat/ödeme (Idempotency-Key), yaşlandırma, ekstre, üretim malzeme maliyeti, fatura PDF'i,
  e-Fatura iskeleti; Finans özeti, Faturalar, Cari hesaplar, Tahsilat & ödeme ekranları.

### Faz 6 — Kurumsal derinleşme
- **S28 kurumsal güvence (ADR-0047):** mutasyon testi (%93,4, CI eşiği %90); schemathesis
  sertleştirme taraması (88 uçta 500 → 0; girdi kaynaklı veritabanı hataları 422/409);
  Redis/MinIO/MQTT/DB kesintisinde zarif bozulma, veri kaybı yok; TOTP sırrı ve webhook imza
  anahtarı alan düzeyinde şifreli; görev ayrımı kişi düzeyinde (kendi talebini onaylama 403);
  rapor hazır bildirimi artık üretiliyor; SBOM, Dependabot, gitleaks; olay müdahale ve nöbet
  runbook'ları, kullanıcı el kitabı, yönetici kılavuzu, API portalı (`docs/api/`), ISO 27001/9001
  eşlemesi, sürüm notları betiği.
- **S27 platform deneyimi (ADR-0045, ADR-0046):** Onaylarım, ⌘K içerik araması, derin bağlantı,
  code-split; 23 listede CSV/Excel dışa aktarma, sipariş PDF'i, yazdırma, WCAG 2.1 AA pası;
  iş günü Europe/Istanbul'dan.
- **S26 kalite, İSG, İK (ADR-0025, ADR-0044):** kontrol planı + SPC, ölçüm cihazı + kalibrasyon,
  zamanlanmış sözleşme/SLA/kalibrasyon taramaları; izin hakedişi, org şeması, eğitim matrisi, KKD,
  tatbikat, kazadan CAPA.
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
