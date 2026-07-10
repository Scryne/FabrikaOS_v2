# FabrikaOS — Yol Haritası (Faz & Sprint Planı)

Bu belge, `FabrikaOS_Proje_Plani.pdf` şartnamesinin **uygulanabilir, görev-görev** yol
haritasıdır: 7 faz / 28 sprint (Faz 6 = GA sonrası kurumsal derinleşme), her sprint için
kapsam + kabul kriteri + Definition of Done (DoD).
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
| | S9 | Stok & Satınalma | ✅ ADR-0011 |
| | S10 | Kalite & Enerji | ✅ ADR-0012 |
| | S11 | İSG & İK | ✅ ADR-0013 |
| | S12 | CRM/Sözleşme/Talep + DYS + Duyuru + Ticari pano | ✅ ADR-0014 |
| **3 — Zekâ** | S13 | AI/ML çekirdeği | ✅ ADR-0015 |
| | S14 | Analitik & Raporlama | ✅ ADR-0016 |
| | S15 | Dijital ikiz + Kiosk | ✅ ADR-0017 |
| **4 — Lisanslama & Dış Entegrasyon** | S16 | Abonelik, Entitlement & Feature Flag | ✅ ADR-0018 |
| | S17 | Platform Admin Paneli | ✅ ADR-0019 |
| | S18 | Dış Portal + Webhook + API Entegrasyon | ⬜ |
| **5 — Operasyon & GA** | S19 | Gözlemlenebilirlik | ⬜ |
| | S20 | Yedekleme/DR + Staging | ⬜ |
| | S21 | Tohumlama & Pilot | ⬜ |
| | S22 | UAT + Sertleştirme + GA `v1.0.0` | ⬜ |
| **6 — Kurumsal Derinleşme** (GA sonrası, v1.x) | S23 | Kurumsal güvenlik & uyum (2FA/SSO, denetim kaydı, KVKK self-servis) | ⬜ |
| | S24 | Üretim & bakım derinleşmesi (vardiya, duruş, ürün/BOM, izlenebilirlik, MTBF/MTTR) | ⬜ |
| | S25 | Tedarik zinciri derinleşmesi (depo/lokasyon, sayım, barkod, satınalma siparişi, tedarikçi skoru) | ⬜ |
| | S26 | Kalite/İSG/İK kurumsal tamamlama (kontrol planı+SPC, kalibrasyon, İSG eğitim, izin hakediş, org şeması) | ⬜ |
| | S27 | Platform deneyimi (bildirim merkezi, birleşik onay kutusu, global arama, UI Master Planı uygulaması) | ⬜ |
| | S28 | Kurumsal güvence (mutation/dayanıklılık testleri, SBOM, SLO, dokümantasyon seti) | ⬜ |
| **7 — Mobil Saha** (tüm fazlar sonrası) | M0–M5 | **"FabrikaOS Saha"** çalışan mobil uygulaması — ayrı master plan: `mobilplani.md` | ⬜ |

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

#### ✅ S9 — Stok & Satınalma (karşılandı — ADR-0011)
`Malzeme`, `StokHareketi` (min/max/kritik); `SatinalmaTalebi` + onay akışı. Uçlar: `/malzemeler`,
`/stok-hareketleri`, `/stok/kritik`, `/satinalma-talepleri` (+`/{id}/onayla`). Olay `stok.kritik`.
**Kabul (karşılandı):** tutulan bakiye + `FOR UPDATE` doğru günceller; kenar-tetikli kritik eşik
uyarısı (bir kez); `satinalma:onay` ayrı izin (görev ayrımı, `depo` rolü 403). Backend + frontend
uçtan uca; fan-out migration + ~29 yeni test.

#### ✅ S10 — Kalite & Enerji (karşılandı — ADR-0012)
Kalite: `KaliteKontrol` (denetim), `Uygunsuzluk`/Tam CAPA (saf durum makinesi `acik→kok_neden→
aksiyon_plani→uygulama→dogrulama→kapandi`, +iptal; `CapaAksiyon` düzeltici/önleyici). Enerji:
`EnerjiTuketim` (hypertable) + trend (continuous aggregate `enerji_tuketim_saatlik`,
`autocommit_block` + real-time aggregation). Uçlar: `/kalite-kontrolleri`, `/uygunsuzluklar`
(+`/{id}/durum`, `/{id}/aksiyonlar`), `/enerji-tuketimleri` (+`/trend`). Olaylar `kalite.kontrol`,
`kalite.uygunsuzluk`, `enerji.olcum`; izin `enerji:yaz` + `kalite`/`enerji` rolleri.
**Kabul (karşılandı):** CAPA yaşam döngüsü + geçersiz geçiş 409 + `kalite:yaz` 403; enerji trendi
doğru toplulaştırılır (real-time). Backend + frontend uçtan uca; fan-out + CAGG migration testli.

#### ✅ S11 — İSG & İK (karşılandı — ADR-0013)
İSG: `IsKazasi`/ramak-kala (domain olayı `isg.kaza`), `RiskDegerlendirme` (saf risk matrisi
olasılık×şiddet → skor/seviye sunucuda). İK: `Personel` özlük (KVKK: TC maskeleme + `ik:oku`
erişim kısıtı), `IzinTalebi` (onay akışı `taslak→onay_bekliyor→onaylandi/reddedildi`+iptal,
`FOR UPDATE`, ayrı `ik:onay` görev ayrımı), fazla mesai, zimmet (iade), sertifika. Uçlar:
`/is-kazalari`, `/risk-degerlendirmeleri`, `/personeller`, `/izin-talepleri` (+`/gonder|onayla|
reddet|iptal`), `/fazla-mesailer`, `/zimmetler` (+`/iade`), `/sertifikalar`. Roller: `isg`,
`ik`, `ik-onaylayan`.
**Kabul (karşılandı):** Kaza/risk + matris skoru; izin talebi akışı + geçersiz geçiş 409 +
`ik:onay` 403; KVKK özlük minimizasyonu (TC maskeli) + erişim kısıtı. Backend + frontend uçtan
uca; fan-out migration (7 tablo) up/down testli; +47 backend testi.

#### ✅ S12 — CRM/Sözleşme/Talep + DYS + Duyuru + Ticari pano (karşılandı — ADR-0014)
CRM: `Firma` (müşteri/tedarikçi) + `Ortak` (kontak). `Sozlesme` (oto kod `SZ-`, durum makinesi,
kenar-tetikli `sozlesme.yaklasiyor` outbox + `/yaklasan` görünüm/`/yaklasanlari-tara`). `Talep`
(oto kod `TL-`, durum makinesi + atama). DYS: `Belge` + `BelgeSurumu` (append-only, içerik
**MinIO/S3 nesne deposunda**, tenant-izole anahtar öneki; `NesneDepo` soyutlaması; multipart
yükle/indir). `Duyuru` (oto kod `DUY-`, yayınla → `duyuru.yeni` gerçek-zaman). Ticari pano
`GET /ticari/ozet`. Roller: `crm`, `dokuman`, `duyuru`.
**Kabul (karşılandı):** Sürümlü doküman yükle/indir (tenant-izole nesne öneki) + eski sürüm
korunur; sözleşme yaklaşan bildirimi (bir kez); modüller menüde RBAC'a göre. Backend + frontend
uçtan uca; fan-out migration (7 tablo) up/down testli; +57 backend testi.

> **🚦 Faz 2 Geçiş Kapısı (GEÇİLDİ):** Saha verisi otomatik akıyor; iş modülleri çekirdeği
> uçtan uca + izole.

---

### FAZ 3 — Zekâ · ~3 sprint
**Amaç:** AI tahminleri, analitik panolar, raporlama, dijital ikiz ve kiosk modu.

#### ✅ S13 — AI/ML çekirdeği (karşılandı — ADR-0015)
Feature pipeline (pandas, saf) + dört model (scikit-learn, saf, deterministik): kestirimci
bakım (RandomForest risk skoru/seviye), anomali (IsolationForest + **`anomali.tespit`**
outbox), OEE tahmini (Ridge lag, 7 günlük ufuk), stok ihtiyaç (kalan gün + önerilen sipariş).
Model artefaktları MinIO'da **sürümlü** (`tenant_<slug>/model/<tur>/<surum>/`, `NesneDepo`);
`model_kayitlari` kayıt defteri (tur başına tek aktif) + `tahminler` çıkarım geçmişi.
Eğitim: `POST /tahmin/egit` → 202 + süreç-içi asyncio görevi (🔧 Celery yerine; ADR-0015).
Uçlar: `/tahmin/{kestirimci-bakim,oee,stok,anomali}` + `/tahmin/{modeller,gecmis}` (`ai:oku`;
eğitim `ai:egit` görev ayrımı). Frontend: Zekâ menüsü + AI Tahminleri ekranı.
**Kabul (karşılandı):** Modeller tenant verisiyle eğitilir/çıkarım yapar (izolasyon testli);
çıktı doğrulama testleri; AI uçları izinli (403) + izole (404); `anomali.tespit` outbox testli.

#### ✅ S14 — Analitik & Raporlama (karşılandı — ADR-0016)
Analitik: `GET /analitik/kpi` (tek çağrıda üretim/OEE + makine + iş emri + stok + kalite +
enerji + İSG + bakım KPI'ları; dönem OEE toplamlardan `oee_hesapla` ile) + `GET /analitik/trend`
(günlük üretim/OEE serisi) — migrationsız salt-okunur toplulaştırma, `analitik:oku`.
Raporlama: saf üretici (`RaporIcerik` → ReportLab **PDF** / openpyxl **XLSX**), 5 tür
(uretim/stok/kalite/enerji/isemri); `POST /raporlar` → **202 + süreç-içi async görev**
(ADR-0015 deseni) → MinIO'ya `tenant_<slug>/rapor/...` anahtarıyla yazılır →
`GET /raporlar/{id}/indir` (hazir değilse 409); durum `kuyrukta→hazirlaniyor→hazir|basarisiz`;
`rapor.hazir` gerçek-zaman olayı. Rol `analist` (rapor:yaz görev ayrımı). Frontend: Analitik
pano (KPI kartları + trend) + Raporlar ekranı (oluştur/izle/indir, canlı yenileme).
**Kabul (karşılandı):** Rapor async üretilir, MinIO'ya yazılır, indirilebilir (bayt eşleşmesi
testli); panolar doğru KPI gösterir (izole tenant'ta sayısal doğrulama); RBAC 403 + tenant
izolasyonu 404 testli; migration fan-out up/down testli. +35 backend testi.

#### ✅ S15 — Dijital ikiz + Kiosk (karşılandı — ADR-0017)
Dijital ikiz = mevcut verinin üstünde **ince yerleşim katmanı**: `ikiz_dugumleri`
(makine başına x/y **yüzde koordinat** + bölge; migration fan-out up/down testli);
`GET/PUT /ikiz/yerlesim` (PUT **replace-all**, 422 doğrulama, `ikiz.yerlesim`
gerçek-zaman) + `GET /ikiz/durum?saat=` (yerleşim ⋈ canlı makine durumu + makine-başı
pencere OEE'si + yerleşmemiş liste + tesis özeti; `donem_oee` yeniden kullanımı) —
ikiz ekranı ve kiosk'un **tek veri kaynağı**. Frontend: `/ikiz` **SVG tesis şeması**
(durum LED'leri, sürükle-yerleştir düzenleme modu, canlı invalidate) + `/kiosk`
**kabuksuz tam ekran** büyük pano (KPI + makine karoları, WS + 30 sn yoklama).
Rol `kiosk` = {uretim:oku}.
**Kabul (karşılandı):** Kiosk salt-okunur (API seviyesinde: yazma uçları 403 testli) +
oturum-dayanıklı (sessiz giriş + WS reconnect + yoklama); ikiz canlı makine durumunu
yansıtır (olay → invalidate); yerleşim/durum uçları RBAC + tenant izolasyon testli.

> **🚦 Faz 3 Geçiş Kapısı (GEÇİLDİ):** Tahmin + analitik + ikiz + kiosk çalışıyor.

---

### FAZ 4 — Lisanslama & Dış Entegrasyon · ~3 sprint
**Amaç:** Modül modül lisanslama (entitlement), platform yönetimi, dış self-servis ve webhook/API.

#### ✅ S16 — Abonelik, Entitlement & Feature Flag
`planlar` (modül seti JSONB + koltuk limiti; deneme/temel/profesyonel/kurumsal) +
tenant-başına `modul_haklari`/`ozellik_bayraklari` override tabloları (public migration,
plan seed + `abonelik.plan_kodu` FK); **`modul_gerekli(kod)` dependency** 19 modül
router'ında (kapalı → 403 `MODUL_KAPALI`, admin dahil — entitlement ≠ RBAC); koltuk
limiti kullanıcı oluşturmada `FOR UPDATE` + sayım (aşım → 409 `KOLTUK_LIMITI`, pasif
sayılmaz); önbelleksiz sorgu = değişim anında etkili. Uçlar: `GET /moduller` (oturum;
menü süzgeci) + `GET /abonelik` (`abonelik:oku`). FE: menü entitlement süzgeci +
`ModulKapisi` upsell boş durumu + `/abonelik` ekranı (plan kartı, koltuk progress,
modül matrisi, "deneysel" rozetleri). Entitlement yazma API'si S17'de (CLI:
`scripts/entitlement_ayarla.py`). ADR-0018.
**Kabul (karşılandı):** Kapalı modüle erişim backend (403 testli) + UI'da engellenir;
koltuk limiti aşımı engellenir (eşzamanlılık kilitli); entitlement değişimi anında
etkili (testli); bypass güvenlik testi (tüm izinli admin yine 403) + tenant izolasyonu.

#### ✅ S17 — Platform Admin Paneli (control-plane) (karşılandı — ADR-0019)
Ayrık kimlik düzlemi: `public.platform_yonetici` + `platform_access/refresh` JWT
tipleri (tenant token'ı platform ucunda ve tersi yapısal 401; rotasyon + rate limit
aynı çekirdek). Uçlar `/api/v1/platform/*`: kimlik · tenantlar (liste+arama+koltuk
kullanımı, detay+entitlement matrisi, **senkron provizyon**, PATCH ad/plan,
askıya-al/aktifleştir, DELETE `onay=slug` + `DROP SCHEMA CASCADE`) · **entitlement
yazma** (S16 devri: PUT modul-haklari/ozellik-bayraklari, `null`=plana dön) ·
abonelikler · planlar · saglik (db/redis/nesne depo sondaları) · **KVKK ihracı**
(`tenant_ihraclari` + 202 süreç-içi görev; `information_schema` keşifli tam şema
dump → ZIP → `platform/ihrac/...`; indirme 409 korumalı). Platform yazmaları
`platform_denetim_izi`'nde. FE: `/platform/*` ayrı düzlem (ayrı store/istemci,
X-Tenant yok) — turuncu hat + PLATFORM filigranı; tenant listesi/detayı (switch
matrisi, slug-yazarak-onay tehlikeli aksiyonlar), provizyon sihirbazı, sağlık panosu.
**Kabul (karşılandı):** provizyon→yeni admin girişi testli; askıya alma erişimi
ANINDA keser (404, giriş dahil); ihraç ZIP'i bilinen veriyi bayt düzeyi doğrulamayla
içerir; entitlement yazımı bir sonraki istekte etkili; migration public up/down.

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

### FAZ 6 — Kurumsal Derinleşme & Mükemmelleştirme · ~6 sprint (GA sonrası, v1.x → v2.0 adayı)
**Amaç:** GA'daki ürünü "çalışan modüller"den **kurumsal sınıf bir platforma** taşımak:
her modülün sektör-standart derinliğe tamamlanması (MES/WMS/QMS olgunluğu), kurumsal
güvenlik & uyum (2FA/SSO, denetim kaydı görünürlüğü, KVKK self-servis), birleşik
bildirim/onay deneyimi ve sürdürülebilir kalite güvencesi.

**İlkeler (tüm Faz 6 sprintlerinde geçerli):**
- **Yeni çekirdek icat edilmez** — mevcut desenler yeniden kullanılır: saf durum makinesi,
  transactional outbox (`GidenOlay`), `FOR UPDATE` satır kilidi, `NesneDepo` (MinIO),
  `/ozet` toplulaştırma, Alembic fan-out, `require_perm` görev ayrımı, 202+süreç-içi async görev.
- Her sprint **dikey dilim**: migration (fan-out up/down) + API + FE ekran + birim/entegrasyon
  testi + canlı uçtan uca doğrulama. Global DoD aynen geçerli.
- Kapsam disiplini modül başına **MoSCoW** ile korunur; "olsa güzel olur" kalemler sprint
  sonunda ADR'ye ertelenmiş-işler olarak yazılır.
- UI tarafının tek doğruluk kaynağı **`uiplani.md` (UI/UX Master Planı v2)**'dir; her yeni
  ekran oradaki modül çalışma alanı desenine (OzetSerit + zengin tablo + board/analiz) uyar.
- Sıralama esnektir: S27 (platform deneyimi) Faz 4 ile paralel öne çekilebilir; S23'ün
  güvenlik kalemleri S22 sertleştirmesiyle koordine edilir.

#### ⬜ S23 — Kurumsal Güvenlik & Uyum
Kimlik sertleştirme: **TOTP 2FA** (QR kurulum + kurtarma kodları; tenant bazlı zorunlu
kılınabilir), **kurumsal SSO** (OIDC; Azure AD/Google Workspace ile test), parola politikası
(uzunluk/geçmiş/yaş, control-plane'de tenant ayarı), **oturum & cihaz yönetimi**
(`GET /kimlik/oturumlar` + uzaktan sonlandırma; refresh token ailesi zaten Redis'te),
opsiyonel tenant IP izin listesi. **Denetim kaydı görünürlüğü:** `core/audit.py` çıktısı
için `GET /denetim-kayitlari` (filtre: kullanıcı/kaynak/eylem/tarih aralığı; append-only
garanti + saklama politikası) + FE görüntüleyici (fark/detay çekmecesi). **KVKK paketi:**
kişisel veri envanteri belgesi, kişi bazlı ihraç (`POST /kvkk/ihrac` → 202 async → MinIO
`tenant_<slug>/kvkk/...` → indir; S14 rapor deseni), anonimleştirme/silme akışı (zincirleme
maskeleme, denetim izli), aydınlatma/consent kayıt tablosu. ISO 27001 kontrol eşleme
dokümanı başlangıcı (`docs/uyum/`).
**Kabul:** 2FA'lı giriş uçtan uca (yanlış kod reddi + kurtarma kodu); denetim ekranında
kim-ne-ne zaman filtrelenebilir ve kayıt değiştirilemez; kişi bazlı ihraç dosyası tüm
modüllerdeki kişisel veriyi kapsar (test: bilinen veriyle bayt düzeyi kontrol); tüm yeni
uçlar RBAC 403 + tenant izolasyonu testli. ADR-0021.

#### ⬜ S24 — Üretim & Bakım Derinleşmesi (MES olgunluğu)
**Vardiya:** `Vardiya` tanımları (ad, saat aralığı, takvim) + üretim verisi/OEE'nin vardiya
kırılımı (`/oee/ozet?vardiya=`). **Duruş yönetimi:** `DurusNedeni` kataloğu (planlı/plansız
sınıfı) + `DurusKaydi` (makine, aralık, neden, açıklama) → OEE kullanılabilirliği gerçek
duruşlardan hesaplanır (mevcut `oee_hesapla` saf çekirdeği girdi kaynağı değişerek korunur);
duruş **pareto** analizi ucu. **Ürün & Reçete (BOM):** `Urun`, `Recete`+`ReceteKalemi`
(malzeme bağlantısı, miktar/birim); iş emrine ürün bağlama; kapanışta BOM patlatma →
**otomatik stok tüketim hareketi** (S9 hareket çekirdeği + idempotency yeniden kullanımı,
opsiyonel/ayarlı). **İzlenebilirlik:** üretim verisine lot/parti numarası + ileri/geri
izleme sorgusu (`/izlenebilirlik?lot=`). **Bakım olgunluğu:** `ArizaKaydi` ↔ bakım iş emri
bağlantısı; **MTBF/MTTR** metrik uçları (saf hesap fonksiyonu, birim testli); bakım
takviminden **otomatik iş emri üretimi** (zamanlanmış tarama, kenar-tetikli, bir-kez
garantisi outbox'la); yedek parça = malzeme ilişkisi.
**Kabul:** Duruş kaydı girildiğinde dönem OEE'si deterministik değişir (birim + entegrasyon);
BOM patlatma doğru miktarları tüketir ve idempotent (çift kapanış çift hareket üretmez);
lot ileri/geri izleme zinciri doğru; MTBF/MTTR bilinen seriyle doğrulanır; otomatik bakım
iş emri bir-kez üretilir; migration fan-out up/down. ADR-0022.

#### ⬜ S25 — Tedarik Zinciri Derinleşmesi (WMS & satınalma olgunluğu)
**Depo/lokasyon:** `Depo` + `Lokasyon` hiyerarşisi; stok hareketlerine lokasyon boyutu +
**transfer** hareketi (çift bacak, tek transaction). **Stok sayımı:** `SayimOturumu` →
sayım satırları → fark raporu → **onaylı düzeltme hareketi** (ayrı `stok:duzeltme` izni —
görev ayrımı, S9 onay deseni). **Barkod/QR:** malzeme etiketi PDF üretimi (S14 ReportLab
yeniden kullanımı) + koddan hızlı arama. **Satınalma Siparişi (PO):** onaylanmış talepten
`SatinalmaSiparisi` (tedarikçi = CRM `Firma` bağlantısı, oto kod `SS-`); **teslim alma** →
stok giriş hareketi, kısmi teslimat destekli; üç yönlü eşleme iskeleti (sipariş–irsaliye–
fatura alanları; e-Fatura entegrasyonu Faz 4 S18 API anahtarı üstünden). **Tedarikçi
performansı:** zamanında-teslim + kalite skoru (kalite kontrol bağlantısı; saf skor
fonksiyonu) → firma detayında.
**Kabul:** Transfer iki bacağı atomik (kısmi yazım imkânsız — test); sayım farkı onaysız
uygulanamaz (403) ve onay sonrası bakiye doğru düzelir; PO→kısmi teslim→stok bakiye zinciri
uçtan uca testli; tedarikçi skoru deterministik; migration fan-out up/down. ADR-0023.

#### ⬜ S26 — Kalite, İSG & İK Kurumsal Tamamlama (QMS olgunluğu)
**Kalite:** `KontrolPlani` (ürün/operasyon başına karakteristik + tolerans); **SPC**
(X̄-R kontrol grafiği verisi + Western Electric kural ihlali tespiti — saf fonksiyon,
birim testli; ihlalde `kalite.spc_ihlal` outbox); `OlcumCihazi` + **kalibrasyon takibi**
(sertifika, geçerlilik; yaklaşan kalibrasyon kenar-tetikli hatırlatma — S12 `yaklasan`
deseni); uygunsuzluk ↔ tedarikçi/üretim kaynağı bağlantısı. **İSG:** İSG eğitimleri +
katılım matrisi; KKD ihtiyacı ↔ İK zimmet entegrasyonu (S11 zimmet yeniden kullanımı);
acil durum tatbikat kayıtları; kaza → CAPA köprüsü (uygunsuzluk otomatik açma, opsiyonel).
**İK:** **izin hakediş bakiyesi** (yıllık hakediş + devir kuralı; onay bakiyeden düşer,
aşım 409); vardiya planlama = S24 `Vardiya` + personel atama; organizasyon şeması
(birim/pozisyon hiyerarşisi, `Personel.yonetici_id`); işe giriş/çıkış kontrol listesi.
**Kabul:** SPC bilinen seriyle doğru sinyal üretir (birim test); kalibrasyon hatırlatması
bir-kez; izin onayı bakiye düşer + bakiye aşımı 409 + `ik:onay` görev ayrımı korunur;
kaza→CAPA köprüsü izolasyon/RBAC testli; migration fan-out up/down. ADR-0024.

#### ⬜ S27 — Platform Deneyimi: Bildirim, Onay Kutusu & UI Master Planı
**Bildirim merkezi:** `Bildirim` (kişi-hedefli, tenant içi) — outbox olaylarından üretim
(stok.kritik, sozlesme.yaklasiyor, anomali.tespit, rapor.hazir, kalite.spc_ihlal...);
zil → gerçek panel (okundu yönetimi, tümünü okundu say), **tercih ekranı** (olay türü
başına aç/kapa), e-posta kanal iskeleti (SMTP + şablon; digest opsiyonel). **Birleşik
onay kutusu:** `GET /onaylarim` (satınalma talebi + izin talebi + sayım düzeltme + ...
bekleyenleri tek listede, rol-duyarlı) + FE "Onaylarım" ekranı. **Global arama:** ⌘K
komut paleti gezinmeye ek **içerik arama** (makine/malzeme/firma/belge/iş emri/personel —
modül başına hafif arama ucu, RBAC süzgeçli). **UI Master Planı uygulaması:** `uiplani.md`
v2'nin kalan tüm kalemleri — `/ozet` uçları + OzetSerit tüm modüllerde, liste↔board
görünümleri, zengin detay profilleri, toplu **CSV/XLSX içe-dışa aktarma çerçevesi**
(her liste ekranında), yazdırma şablonları. **Erişilebilirlik & performans:** WCAG 2.1 AA
denetimi (klavye/odak/kontrast/aria) + düzeltmeler; rota-düzeyi code-split + bundle
bütçesi; backend N+1 taraması + indeks gözden geçirmesi.
**Kabul:** Bildirim canlı düşer + okundu kalıcı + tercih kapatınca üretilmez; onay
kutusunda ≥2 modülün bekleyenleri tek listede ve aksiyon alınabilir; ⌘K'den kayda
gidilir (RBAC dışı sonuç sızmaz — test); dışa aktarma büyük veri setinde zaman aşımı
yaşamaz (async 202 deseni); Lighthouse erişilebilirlik ≥95; tüm FE/BE test + codegen yeşil.
ADR-0025.

#### ⬜ S28 — Kurumsal Güvence & Sürdürülebilirlik
**Test derinliği:** mutation testing (mutmut/Stryker) kritik çekirdekte (OEE, durum
makineleri, tenancy) skor eşiğiyle; schemathesis kapsam genişletme; **dayanıklılık
senaryoları** — Redis/MinIO/MQTT kesintisinde davranış (zarif bozulma + kurtarma + veri
kaybı yok) otomasyonlu; gerçekçi k6 yük profilleri (NFR başına senaryo). **Tedarik zinciri
güvenliği:** SBOM (CycloneDX) CI artefaktı; bağımlılık tarama otomasyonu (pip/npm audit +
Dependabot/Renovate); imaj imzalama; gizli tarama pre-commit. **Operasyon:** runbook seti
(olay müdahale, on-call, DR tatbikat takvimi) `docs/operasyon/`; SLO/SLA tanımları + hata
bütçesi panosu (S19 Grafana üstüne). **Dokümantasyon:** kullanıcı el kitabı (modül modül,
TR), yönetici kılavuzu, geliştirici API portalı (OpenAPI'den statik site), sürüm notları
otomasyonu (Conventional Commits → CHANGELOG); ISO 27001/9001 kontrol eşlemesi tamamlanır.
**Mevcut modül sertleştirme pası:** modül modül hata avı (form validasyon uçları, boş/aşırı
veri, eşzamanlılık) — bulunanlar bu sprintte kapatılır.
**Kabul:** Mutation skoru eşiği CI'da; üç kesinti senaryosu da testli ve veri kaybı yok;
SBOM her build'de üretilir; doküman seti yayınlanmış ve sürüm treniyle güncellenebilir;
sertleştirme pası bulguları kapatılmış. ADR-0026.

> **🚦 Faz 6 Kapısı (Kurumsal Olgunluk):** Modüller sektör-standart derinlikte (vardiya/
> duruş/BOM/izlenebilirlik + depo/sayım/PO + SPC/kalibrasyon + hakediş/org) + kurumsal
> güvenlik & uyum (2FA/SSO + denetim + KVKK self-servis) + birleşik bildirim/onay + kalite
> güvence hattı → ürün **kurumsal müşteriye satılabilir olgunlukta**; `v2.0` adayı.

---

### FAZ 7 — Mobil Saha Uygulaması ("FabrikaOS Saha") · M0–M5 (tüm fazlar sonrası; ayrı master plan)
**Amaç:** Fabrika çalışanlarının cebindeki **görev-odaklı saha terminali** — web'in
kopyası değil: rol paketleri (operatör/bakım/depo/kalite/İSG/self-servis/yönetici),
**offline-first store-and-forward** (edge deseninin kullanıcı katmanı, `Idempotency-Key`),
QR/NFC "makineye dokun", tek-tuş ramak kala, vardiya cihazı modu (paylaşımlı tablet +
rozet-QR/PIN), push bildirim + Onaylarım. React Native + Expo, mevcut API/WS ve OpenAPI
codegen tiplerinin paylaşımı; ADR-0027+.
Kapsam, mimari, kilometre taşları (M0–M5), NFR ve kabul kriterleri: **`mobilplani.md`**.
**Bağımlılıklar:** S16 (entitlement), S23 (oturum/2FA), S25 (barkod/sayım), S27 (bildirim);
asgari erken-başlama kümesi mobilplani §13'te.

---

## Faz geçiş kapıları (özet)

| Kapı | Şart | Durum |
|---|---|---|
| Faz 0 | İzolasyon + provizyonlama + RBAC + fan-out testleri yeşil | ✅ geçildi |
| Faz 1 (MVP) | Üretim/OEE + iş emri uçtan uca, canlı, izole, korumalı | ✅ geçildi |
| Faz 2 | Saha verisi otomatik; iş modülleri çekirdeği tam + izole | ✅ geçildi |
| Faz 3 | AI tahmin + analitik + rapor + ikiz + kiosk | ✅ geçildi |
| Faz 4 | Entitlement + platform admin + webhook/dış portal | ⬜ |
| GA | NFR + güvenlik/KVKK + dokümantasyon + UAT kabul | ⬜ |
| Faz 6 | Modül derinliği (MES/WMS/QMS) + kurumsal güvenlik/uyum + bildirim/onay + güvence → `v2.0` adayı | ⬜ |
| Faz 7 (Mobil) | `mobilplani.md` M0–M5 + offline kayıpsız + push izole + saha pilotu → mağaza yayını `saha-v1.0.0` | ⬜ |

---

## Riskler & azaltım

| Risk | Azaltım |
|---|---|
| R1 — 27 modül kapsam şişmesi | MoSCoW + MVP-öncelik; faz kapıları |
| R3 — Çok-kiracı veri sızıntısı | `search_path` tek-nokta disiplini + zorunlu izolasyon testleri |
| R6 — Migrasyon fan-out hatası | Fan-out DoD'de; CI'da iki-şema testi; downgrade zorunlu |
| R5 — Edge/MQTT zorluğu | Store-and-forward; erken simülatörle test; gerekirse ertele |
| R7 — Performans (Timescale) | Continuous aggregate + indeks; yük testi (NFR) |
| R8 — Faz 6 derinleşme kapsam şişmesi | Modül başına MoSCoW; dikey dilim sprintler; mevcut çekirdek desenlerin (outbox, durum makinesi, `NesneDepo`, `/ozet`, fan-out) yeniden kullanımı — yeni çekirdek icat yasağı |
