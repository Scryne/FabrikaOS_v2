# FabrikaOS — Yol Haritası (Faz & Sprint Planı)

Bu belge, `FabrikaOS_Proje_Plani.pdf` şartnamesinin **uygulanabilir, görev-görev** yol
haritasıdır: 6 faz / 22 sprint, her sprint için kapsam + kabul kriteri + Definition of Done (DoD).
Çalışma modeli **TDD disiplinli** (kırmızı → yeşil → refactor → doğrulama → DoD) ve **trunk-based**'tir.

> Kaynak şartname: `FabrikaOS_Proje_Plani.pdf` (46 sayfa, FR/NFR + REST spesifikasyonu + test/güvenlik/DR).

---

## Durum özeti

| Faz | Sprint | Konu | Durum |
|---|---|---|---|
| **0 — Temel** | S1 | Proje iskeleti + çekirdek | ✅ `4fdbe44` |
| | S2 | Çok kiracılılık + Kimlik & RBAC | ✅ `3d79cda` |
| **1 — MVP** | S3 | Üretim & OEE (backend) | ✅ `8e00374` |
| | S4 | İş Emirleri & Bakım (backend) | ✅ `b0284c4` |
| | S5 | SPA iskeleti + Auth (frontend) | ✅ `715211d` |
| | — | Tasarım geçişi: nötr antrasit tema + pano önizleme | ✅ `9fb9454` |
| | S6 | Üretim/İş emri ekranları + sayfalama/filtre | ✅ `a9fc5e6` |
| | **S7** | Gerçek zaman çekirdeği + uçtan uca + izolasyon | ✅ |
| **2 — Saha & Modüller** | S8 | Edge & Ingestion | ✅ ADR-0010 |
| | S9 | Stok & Satınalma | ⬜ |
| | S10 | Kalite & Enerji | ⬜ |
| | S11 | İSG & İK | ⬜ |
| | S12 | CRM/Sözleşme/Talep + DYS + Duyuru | ⬜ |
| **3 — Zekâ** | S13 | AI/ML çekirdeği | ⬜ |
| | S14 | Analitik & Raporlama | ⬜ |
| | S15 | Dijital ikiz + Kiosk | ⬜ |
| **4 — Lisanslama & Dış Entegrasyon** | S16 | Abonelik, Entitlement & Feature Flag | ⬜ |
| | S17 | Platform Admin Paneli | ⬜ |
| | S18 | Dış Portal + Webhook + API Entegrasyon | ⬜ |
| **5 — Operasyon & GA** | S19 | Gözlemlenebilirlik | ⬜ |
| | S20 | Yedekleme/DR + Staging | ⬜ |
| | S21 | Tohumlama & Pilot | ⬜ |
| | S22 | UAT + Sertleştirme + GA `v1.0.0` | ⬜ |

İşaretler: ✅ tamam · ▶ sıradaki · ⬜ planlı.

---

## Çalışma modeli

### Sprint döngüsü (her sprint)
1. **Hazırlık (DoR):** görevler netleşir, kabul kriterleri okunur.
2. **Kırmızı:** önce başarısız test (birim/entegrasyon).
3. **Yeşil:** testi geçiren en yalın kod.
4. **Refactor:** temizlik; lint + tip kontrolü geçer.
5. **Doğrulama:** `docker compose up` ile uçtan uca davranış + kabul kriterleri.
6. **İnceleme & Commit:** Conventional Commits + gerekli ADR.
7. **Kapanış (DoD):** global DoD + sprint'e özel ek maddeler.

### Global Definition of Done — her sprintte zorunlu
- [ ] `ruff` + `mypy` (backend) / ESLint + `tsc --strict` (frontend) temiz.
- [ ] Birim + entegrasyon testleri yazıldı ve geçiyor.
- [ ] **Tenant izolasyon testi:** yeni veri uca başka tenant'tan erişilemediği test edildi.
- [ ] **RBAC testi:** yetkisiz rol 403, yetkili rol erişir.
- [ ] API yanıtları standart zarf (`{success, message, data, meta}`) + doğru HTTP kodu.
- [ ] OpenAPI/Swagger güncel; sözleşme testi (schemathesis) kırmızı değil.
- [ ] Migrasyon eklendiyse `public` + ≥2 örnek tenant şemasında **fan-out** + downgrade çalıştı.
- [ ] Audit gereken yazma işlemleri kim-ne-ne zaman üretiyor.
- [ ] Gerekli ADR (`docs/adr/NNNN-*.md`) + veri sözlüğü güncel.
- [ ] CI yeşil; staging'e deploy edilebilir.
- [ ] Conventional Commit ile commit edildi.

---

## Kesişen (cross-cutting) standartlar

- **Tenant çözümleme (EN KRİTİK):** subdomain (`fabrika-a.fabrikaos.com`) veya `X-Tenant` header
  → middleware slug'ı çözer, `public.tenant`'tan aktiflik doğrular → istek-kapsamlı işlemde
  `SET LOCAL search_path TO tenant_<slug>, public`. JWT `tenant_slug` ile subdomain eşleşmeli
  (cross-tenant token reddi). `search_path` bağlantı düzeyinde olduğundan **tek noktada** (dependency)
  çözülür ve havuza dönmeden sıfırlanır — yanlış uygulama veri sızıntısıdır (R3).
- **API zarfı:** `{success, message, data, meta}`; sayfalama `?sayfa=&adet=&siralama=&yon=&arama=`
  + alan filtreleri; POST için opsiyonel `Idempotency-Key`.
- **RBAC izin sözlüğü** (Türkçe `kaynak:eylem`): `kullanici:*`, `uretim:*`, `isemri:*`, `bakim:*`,
  `stok:*`, `satinalma:*` (`onay` ayrı), `kalite:*`, `isg:*`, `ik:*`, `enerji:oku`, `crm:oku`,
  `dys:*`, `ai:oku`, `analitik:oku`, `rapor:*`, `dis-panel`, `platform-admin`, `edge`. Her uçta
  `Depends(require_perm("..."))`.
- **Test piramidi:** Birim → Entegrasyon (test DB) → Sözleşme (schemathesis) → E2E (Playwright)
  → Yük (Locust/k6) → Güvenlik (bandit, OWASP ZAP). **7 kritik test ailesi her zaman korunur:**
  tenant izolasyonu, provizyonlama, RBAC, OEE hesaplama, AI çıktısı, migrasyon fan-out,
  KVKK ihraç/silme.
- **CI/CD:** `lint+tip` → `test (tenancy/RBAC + Playwright kritik E2E)` → `güvenlik (pip/npm audit,
  bandit, gizli tarama)` → `build` → `deploy (staging otomatik; prod manuel; migrasyon fan-out)`.

---

## Faz ve sprint planı (komple)

### FAZ 0 — Temel · ~2 sprint
**Amaç:** Çekirdek altyapı, çok kiracılılık ve kimlik/RBAC; üzerine modül inşa edilebilir hale gelsin.

#### ✅ S1 — Proje iskeleti + çekirdek
Monorepo + `pyproject.toml` + ruff/mypy/pre-commit; `docker-compose.yml` (api, db[timescale],
redis, minio, traefik, mqtt); FastAPI app factory + router kaydı; çekirdek (config, logging,
exceptions + handler, responses zarfı, middleware/request_id); `/saglik` + `/docs`; CI iskeleti;
ADR-0001/0002.
**Kabul:** `docker compose up` → API kalkar, `/saglik` 200, `/docs` açık, CI yeşil.

#### ✅ S2 — Çok kiracılılık + Kimlik & RBAC
`public` control-plane + `Tenant`; Alembic `public/`+`tenant/` ağaçları + `naming_convention`;
`core/db/tenancy.py` (`SET LOCAL search_path`, havuz güvenliği); **Alembic fan-out** + downgrade;
idempotent provizyonlama (şema + migrate + seed); OAuth2/JWT (argon2id + rotasyonlu refresh,
Redis iptal); RBAC (`Rol`/`Izin`/`rol_izin`/`kullanici_rol`, `require_perm`); `core/audit.py`;
rate limit. Uçlar: `/api/v1/kimlik/{token,yenile,cikis,ben,parola-degistir}`, `/api/v1/kullanicilar`.
**Kabul:** İki tenant; tenant-A token'ı tenant-B verisine erişemez (izolasyon testi); yetkisiz 403;
audit kaydı; fan-out iki şemada + geri alınır. ADR-0003/0004/0005.

> **🚦 Faz 0 Geçiş Kapısı (GEÇİLDİ):** İzolasyon + provizyonlama + RBAC + fan-out testleri yeşil.

---

### FAZ 1 — MVP · ~5 sprint
**Amaç:** Faz sonunda **gösterilebilir** ürün: üretim/OEE + iş emri, çalışan SPA, canlı güncelleme,
uçtan uca izolasyon.

#### ✅ S3 — Üretim & OEE (backend)
`Makine`, `UretimVerisi` (Timescale **hypertable**), `ArizaKaydi` + migrasyon; **OEE hesaplama**
(Kullanılabilirlik × Performans × Kalite) saf fonksiyon + kapsamlı birim test. Uçlar:
`/makineler` (GET/POST, `/{id}`, `/{id}/durum` PATCH, `/{id}/oee`), `/uretim-verileri` (GET/POST),
`/oee/ozet` — `uretim:oku/yaz` korumalı. ADR-0006.
**Not:** continuous aggregate + compression/retention S10/S19'a bırakıldı (autocommit_block gerekir).

#### ✅ S4 — İş Emirleri & Bakım (backend)
`IsEmri` + **saf durum makinesi** (`acik→atandi→devam_ediyor→kapandi` + her aşamadan `iptal`,
terminalden çıkış yok) + yorum/aktivite; `BakimPlani` (önleyici/kestirimci/periyodik);
`core/olaylar.py` **transactional outbox** (`GidenOlay` + `olay_yayinla`). Durum geçişinde
`FOR UPDATE` satır kilidi; oto kod `IE-{yıl}-{id:06d}`. `is_emri.kapandi` olayı kapanışla aynı
transaction'da yazılır (webhook teslimatı S18). Uçlar: `/is-emirleri` (GET/POST, `/{id}`,
`/{id}/durum` PATCH, `/{id}/yorum` POST), `/bakim-planlari` (GET/POST, `/{id}` GET/PATCH). ADR-0007.

#### ✅ S5 — SPA iskeleti + Auth (frontend)
Vite + React 18 + TS strict + **Ant Design v5 hibrit** (özel koyu "deri"); React Router; TanStack
Query + Zustand. **OpenAPI'den TS codegen** + tiplenmiş `apiClient` (X-Tenant + Bearer, 401→yenile
single-flight); access token bellekte + refresh localStorage (sessiz giriş); RBAC = `KorunanRota`
+ `IzinKapisi` + `gorunurMenu`; i18n TR/EN. ADR-0008. 32 test (Vitest + RTL).

#### ✅ Tasarım geçişi — nötr antrasit tema + pano önizleme (`9fb9454`)
Tema lacivert/amber tohumdan **nötr antrasit + mavi YALNIZ vurgu**'ya çevrildi (rampa R=G=B,
referans #101010/#181818; body mavi parıltı kaldırıldı). Pano önizleme `/onizleme` (yalnız DEV):
KPI kartları, OEE donut, üretim trendi, son üretim tablosu (statik demo veri). `KpiKart` +
`grafik/{Donut,SutunGrafik}`; Inter + JetBrains Mono.

#### ✅ S6 — Üretim/İş emri ekranları + sayfalama/filtre (frontend) (`a9fc5e6`)
Makine listesi/detay (OEE gauge), OEE panosu (**ECharts** gauge/çubuk/donut), üretim verisi
giriş/liste, iş emri **liste + kanban** (durum makinesi aynası, atama-duyarlı geçişler) +
detay çekmecesi; standart **`SunucuTablo`** (sunucu-taraflı sayfalama/sıralama/arama/filtre,
`meta` uyumlu); yönetici 360° pano gerçek veriyle; modül hook'ları (TanStack Query). Backend'e
migrationsız, beyaz-listeli `arama`/`siralama`/`yon` eklendi (uçların gerçekten desteklemesi için).
**Kabul (karşılandı):** Listeler sunucu-taraflı; OEE grafiği gerçek veriyle çizilir; responsive.

#### ✅ S7 — Gerçek zaman çekirdeği + uçtan uca + izolasyon (ADR-0009)
FastAPI **WebSocket** (`/api/v1/ws/olaylar`) + Redis pub/sub, **tenant-kapsamlı kanallar**
(`tenant:<slug>:olaylar` → izolasyon yapısal); yazma uçlarından best-effort yayın
(makine.durum / uretim.eklendi / isemri.durum / isemri.olusturuldu); frontend canlı abonelik
(`GercekZamanSaglayici` → olay başına TanStack Query invalidate) + canlı gösterge; ilk
**Playwright E2E** (başka istemcinin durum değişikliği listede manuel yenileme olmadan görünür).
**Kabul (karşılandı):** Olay yalnız ilgili tenant'a yayılır (izolasyon testi); canlı OEE/durum
panoda güncellenir; WS auth + çapraz-tenant reddi testli; E2E yeşil.

> **🚦 Faz 1 / MVP Geçiş Kapısı (GEÇİLDİ):** Çok-kiracılı üretim/OEE + iş emri uçtan uca,
> **canlı**, izole, korumalı → demo/portföy için kullanılabilir.

---

### FAZ 2 — Saha & Modüller · ~5 sprint
**Amaç:** Sahadan otomatik veri akışı + iş modüllerinin çekirdek üzerinde tamamlanması.

#### ✅ S8 — Edge & Ingestion (ADR-0010)
**Edge Gateway Agent** (`edge/`, bağımsız paket): pluggable `SahaSurucu` (simülatör + OPC-UA/
Modbus iskelet) → edge-side aralık özeti → MQTT (`fabrikaos/<tenant>/<cihaz>/olcum`, QoS1) +
**store-and-forward** (sqlite tampon, kayıpsız replay). Bulut **Ingestion Worker** (aiomqtt;
tenant doğrula → `search_path` → **idempotent** yaz → `uretim.eklendi` yayını). Üç ingestion
yolu tek serviste: MQTT, REST `POST /saha/olcumler` (`edge` izni, toplu), CSV içe aktarma.
Cihaz yönetimi `GET/POST /saha/cihazlar` (`saha:oku/yaz`). Frontend salt-okunur Saha Cihazları
ekranı (canlı `son_gorulme`). Veri `uretim_verileri`'ne yazıldığı için OEE hattı değişmedi.
**Kabul (karşılandı):** Simüle PLC verisi MQTT→ingestion→OEE panosuna **elle giriş olmadan**
akar (gerçek broker round-trip testi); ingestion tenant-aware (izolasyon testli); store-and-forward
kayıpsız + idempotency çift-saymayı önler. mTLS/gerçek OPC-UA/Modbus Faz 5'e ertelendi.

#### ⬜ S9 — Stok & Satınalma
`Malzeme`, `StokHareketi` (min/max/kritik); `SatinalmaTalebi` + onay akışı. Uçlar: `/malzemeler`,
`/stok-hareketleri`, `/stok/kritik`, `/satinalma-talepleri` (+`/{id}/onayla`). Olay `stok.kritik`.
**Kabul:** Stok hareketi bakiyeyi doğru günceller; kritik eşik tetikler; `satinalma:onay` ayrı izin.

#### ⬜ S10 — Kalite & Enerji
Kalite: `KaliteKontrol`, `Uygunsuzluk`/CAPA. Enerji: `EnerjiTuketim` (hypertable) + trend
(continuous aggregate). Uçlar: `/kalite-kontrolleri`, `/uygunsuzluklar`, `/enerji-tuketimleri`.
**Kabul:** CAPA yaşam döngüsü çalışır; enerji trendi doğru toplulaştırılır.

#### ⬜ S11 — İSG & İK
İSG: `IsKazasi`/ramak-kala, `RiskDegerlendirme` (risk matrisi). İK: `Personel` özlük, izin,
fazla mesai, zimmet, sertifika. Uçlar: `/is-kazalari`, `/risk-degerlendirmeleri`, `/personeller`,
`/izin-talepleri`.
**Kabul:** Kaza/risk + matris; izin talebi akışı; KVKK özlük minimizasyonu + erişim kısıtı.

#### ⬜ S12 — CRM/Sözleşme/Talep + DYS + Duyuru + Modül panoları
`Firma`/`Ortak`/`Sozlesme`/`Talep`; DYS `Belge` (sürümlü, MinIO); `Duyuru`/bildirim. Uçlar:
`/firmalar`, `/sozlesmeler`, `/talepler`, `/belgeler`, `/duyurular`. Olay `sozlesme.yaklasiyor`.
**Kabul:** Sürümlü doküman yükle/indir (tenant-izole MinIO öneki); sözleşme bildirimi; modüller
menüde RBAC'a göre.

> **🚦 Faz 2 Geçiş Kapısı:** Saha verisi otomatik akıyor; iş modülleri çekirdeği uçtan uca + izole.

---

### FAZ 3 — Zekâ · ~3 sprint
**Amaç:** AI tahminleri, analitik panolar, raporlama, dijital ikiz ve kiosk modu.

#### ⬜ S13 — AI/ML çekirdeği
Feature pipeline (pandas); modeller: kestirimci bakım, anomali, OEE tahmini, stok ihtiyaç
(scikit-learn) — Celery job; model artefaktları MinIO'da **sürümlü**; tenant-aware eğitim/çıkarım.
Uçlar: `/tahmin/{kestirimci-bakim,oee,stok,anomali}` (`ai:oku`). Olay `anomali.tespit`.
**Kabul:** Modeller tenant verisiyle çalışır; çıktı doğrulama testi; AI uçları izinli + izole.

#### ⬜ S14 — Analitik & Raporlama
KPI analitik panoları (`/analitik/kpi`); rapor üretimi **async job**: ReportLab (PDF), openpyxl
(Excel). Uçlar: `POST /raporlar`, `GET /raporlar/{id}`.
**Kabul:** Rapor async üretilir, MinIO'ya yazılır, indirilebilir; panolar doğru KPI gösterir.

#### ⬜ S15 — Dijital ikiz + Kiosk
Dijital ikiz görselleştirme (tesis/hat şeması — SVG/Leaflet, canlı durum); **kiosk** salt-okunur
büyük ekran üretim panosu.
**Kabul:** Kiosk salt-okunur + oturum-dayanıklı; ikiz canlı makine durumunu yansıtır.

> **🚦 Faz 3 Geçiş Kapısı:** Tahmin + analitik + ikiz + kiosk çalışıyor.

---

### FAZ 4 — Lisanslama & Dış Entegrasyon · ~3 sprint
**Amaç:** Modül modül lisanslama (entitlement), platform yönetimi, dış self-servis ve webhook/API.

#### ⬜ S16 — Abonelik, Entitlement & Feature Flag
`Plan`/`Abonelik`/`Entitlement` (control-plane) + feature flag; **backend entitlement bağımlılığı**
(modül kapalıysa 403/gizle) + **frontend menü** entitlement'e göre; koltuk (seat) limiti. Uçlar:
`/abonelik`, `/moduller`.
**Kabul:** Kapalı modüle erişim engellenir (backend + UI); koltuk limiti aşımı engellenir;
entitlement değişimi anında etkili. Bypass için güvenlik testi.

#### ⬜ S17 — Platform Admin Paneli (control-plane)
Platform uçları (`platform-admin`): tenant listele/oluştur/güncelle/askıya-al/**ihraç**/sil;
`/platform/abonelikler`, `/platform/saglik`. Platform admin SPA.
**Kabul:** Panelden yeni tenant **dakikalar içinde** provizyonlanır; askıya alma erişimi keser;
ihraç tenant verisini eksiksiz dışa aktarır (KVKK).

#### ⬜ S18 — Dış Portal + Webhook + API Entegrasyon
Dış self-servis portal (`dis-panel`): `/dis/talepler`, `/dis/durum`. **Webhook** altyapısı: imzalı
(`X-FabrikaOS-Signature`), sürümlü, retry/sıra; olaylar: `is_emri.kapandi`, `ariza.olustu`,
`stok.kritik`, `oee.dustu`, `sozlesme.yaklasiyor`, `anomali.tespit`. 3. taraf ERP/muhasebe
(Logo/SAP/e-Fatura) için anahtar tabanlı erişim.
**Kabul:** Webhook imza doğrulanabilir, retry korunur; dış portal yalnızca `dis-panel` kapsamı.

> **🚦 Faz 4 Geçiş Kapısı:** Entitlement + platform admin + webhook/dış portal hazır
> (ürün modül modül satılabilir).

---

### FAZ 5 — Operasyon & GA · ~4 sprint
**Amaç:** Üretime hazır operasyon, gözlemlenebilirlik, yedekleme/DR, tohumlama, pilot, UAT, GA.

#### ⬜ S19 — Gözlemlenebilirlik
Yapılandırılmış log (`tenant_id`+`request_id`) + merkezi toplama; Sentry; Prometheus+Grafana;
OpenTelemetry; alerting kuralları.
**Kabul:** Hata Sentry'de tenant/istek bağlamıyla görünür; SLI/SLO panoları yayında; alarm tetiklenir.

#### ⬜ S20 — Yedekleme/DR + Staging
**Tenant-aware yedekleme** (şema bazlı) + geri yükleme; RPO/RTO; restore **tatbikatı** (≥çeyreklik);
staging (anonim veri); prod hazırlık (Traefik wildcard TLS, Let's Encrypt).
**Kabul:** Tek tenant şeması bağımsız geri yüklenir (kanıtlı drill); staging prod'a denk;
migration fan-out deploy çalışır. DR runbook `docs/operasyon/`.

#### ⬜ S21 — Tohumlama & Pilot
Tohumlama: sistem (global referans, `public`), tenant (rol/izin), demo; onboarding CSV içe aktarma;
idempotent seed. **Pilot fabrika** devreye alma; gerçek veriyle çalıştırma.
**Kabul:** `docker compose up` + seed ile sistem anlamlı veriyle açılır; pilot tenant gerçek veriyle.

#### ⬜ S22 — UAT + Sertleştirme + GA `v1.0.0`
**UAT** (pilot kabul); güvenlik sertleştirme (OWASP ZAP, bandit, pentest düzeltmeleri); yük/performans
(Locust/k6, NFR doğrulama); dokümantasyon tamamlama; **GA `v1.0.0`** + CHANGELOG.
**Kabul:** NFR hedefleri karşılanır; kritik güvenlik bulgusu yok; UAT kabul; dokümanlar tam; `v1.0.0`.

> **🚦 GA Kapısı:** 7 kritik test ailesi yeşil + NFR'ler + KVKK/güvenlik + dokümantasyon tam.

---

## Faz geçiş kapıları (özet)

| Kapı | Şart | Durum |
|---|---|---|
| Faz 0 | İzolasyon + provizyonlama + RBAC + fan-out testleri yeşil | ✅ geçildi |
| Faz 1 (MVP) | Üretim/OEE + iş emri uçtan uca, canlı, izole, korumalı | ✅ geçildi |
| Faz 2 | Saha verisi otomatik; iş modülleri çekirdeği tam + izole | ⬜ |
| Faz 3 | AI tahmin + analitik + rapor + ikiz + kiosk | ⬜ |
| Faz 4 | Entitlement + platform admin + webhook/dış portal | ⬜ |
| GA | NFR + güvenlik/KVKK + dokümantasyon + UAT kabul | ⬜ |

---

## Riskler & azaltım

| Risk | Azaltım |
|---|---|
| R1 — 27 modül kapsam şişmesi | MoSCoW + MVP-öncelik; faz kapıları |
| R3 — Çok-kiracı veri sızıntısı | `search_path` tek-nokta disiplini + zorunlu izolasyon testleri |
| R6 — Migrasyon fan-out hatası | Fan-out DoD'de; CI'da iki-şema testi; downgrade zorunlu |
| R5 — Edge/MQTT zorluğu | Store-and-forward; erken simülatörle test; gerekirse ertele |
| R7 — Performans (Timescale) | Continuous aggregate + indeks; yük testi (NFR) |
