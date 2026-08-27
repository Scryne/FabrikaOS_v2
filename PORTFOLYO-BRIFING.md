# PORTFÖY BRİFİNGİ — FabrikaOS

> Bu dosya, portföy sitesi için **veri çıkarma** çıktısıdır; pazarlama metni değildir.
> Her sayının yanında kaynağı vardır. Ölçülmemiş şeyler `BİLİNMİYOR` yazar.
> Çıkarma tarihi: **2026-08-08**. İncelenen ağaç: `90f374f` (`main` == `origin/main` == `feat/s25-tedarik-zinciri`).

---

## 1. Künye

| Alan | Değer | Kaynak |
|---|---|---|
| **Ne yapar** | Fabrikaların üretim sahasından gelen makine verisini canlı toplayıp OEE'ye çeviren ve bunu iş emri, bakım, stok, kalite, İSG/İK, CRM gibi modüllerle tek uygulamada birleştiren, her müşterinin kendi veritabanı şemasında izole olduğu çok kiracılı bir MES+ERP web platformu. | `README.md:12-15`, `PRODUCT.md` "Product Purpose" |
| **Kimin için** | İki birincil kullanıcı: (a) saha/üretim operatörü ve vardiya amiri — tablet/büyük ekran, "tek bakışta durum"; (b) tesis yöneticisi/planlamacı — masada, tablo/filtre/rapor yoğun. Hedef segment metinde "Türkiye'deki orta/büyük ölçekli metal sanayi tesisleri" (README) ile "KOBİ üreticiler" (PRODUCT.md) arasında **tutarsız** — ikisi de yazılı, koddan hangisinin doğru olduğu çıkmıyor. | `PRODUCT.md` "Users", `README.md:12-15` |
| **Çalışma dönemi** | İlk commit **2026-06-29**, son commit **2026-07-31**. Takvimde 33 gün, ama commit atılan **yalnızca 15 gün** var. | `git log --reverse` / `git log -1` |
| **Ara verilen dönemler** | Belirgin tek boşluk: **2026-07-16 → 2026-07-29 (14 gün, sıfır commit)**. Küçük boşluklar: 07-02/03, 07-06, 07-13. Yoğunluk günlere kümelenmiş: 07-10 (27 commit), 07-04 (25), 06-30 (22). | `git log --format=%ad --date=short \| sort \| uniq -c` |
| **Rol** | **Tek geliştirici.** 172/172 commit `Scryne`. Commit gövdelerinde `Co-Authored-By: Claude ...` trailer'ları var (AI eşli programlama); insan katkıcı yok. | `git shortlog -sn --all`, örn. `git show 78a1e37` |
| **Yığın** | Python 3.12 / FastAPI (async) · SQLAlchemy 2.0 + Alembic (iki ağaçlı fan-out) · PostgreSQL 16 + TimescaleDB (hypertable + continuous aggregate) · Redis (pub/sub, refresh iptal listesi, rate limit) · MinIO (S3 uyumlu nesne depolama) · MQTT (aiomqtt) + bağımsız edge ajanı · React 18 + TypeScript (strict) + Vite + Ant Design 5 + ECharts + TanStack Query · scikit-learn/pandas/joblib (ML) | `pyproject.toml:13-32`, `frontend/package.json`, `docker-compose.yml` |
| **Commit sayısı** | **172** | `git rev-list --count HEAD` |
| **İzlenen dosya sayısı** | **769** (`node_modules`, `.venv`, `dist` zaten `.gitignore`'da) — 401 `.py`, 189 `.tsx`, 88 `.ts`, 57 `.md`, 4 `.css` | `git ls-files \| wc -l`, uzantı dağılımı |

### Satır sayısı (üretilmiş dosyalar ayrıştırılmış)

| Kategori | Satır | Kaynak |
|---|---|---|
| Tüm izlenen kod (`py`+`ts`+`tsx`+`css`) | 95.211 | `git ls-files ... \| wc -l` toplamı |
| — eksi üretilmiş `frontend/src/api/types.gen.ts` (openapi-typescript çıktısı) | −17.034 | `wc -l frontend/src/api/types.gen.ts` |
| **= Elle yazılmış kod** | **78.177** | hesap |
| bunun içinde: testler (BE 14.441 + FE 3.966) | 18.407 | `git ls-files "backend/tests/*.py" ...` |
| bunun içinde: Alembic migration dosyaları | 3.201 | `git ls-files "backend/migrations/*/versions/*.py"` |
| **= Uygulama kodu (test/migration/üretilmiş hariç)** | **~56.500** | hesap |
| Markdown dokümantasyon (57 dosya) | 15.329 | `git ls-files "*.md" \| xargs wc -l` |

Not: `frontend/openapi.json` tek satırlık üretilmiş dosyadır (satır sayımına girmez, ~10 bin satırlık JSON toplamının çoğu odur).

---

## 2. Durum

### `geliştirme`

**Gerekçe:** Ürün fonksiyonel olarak geniş ve testli, ama yol haritasının kendi tanımına göre GA'ya (`v1.0.0`) giden Faz 5'in **tamamı** (S19 operasyon, S20 gözlemlenebilirlik, S21 felaket kurtarma, S22 UAT) hiç yazılmamış. Dağıtım, izleme, yedekleme/geri dönüş ve kullanıcı kabulü yoksa "GA öncesi" demek kapıyı iptal eder.

**Ölçülebilir ayrıntılar (bu oturumda çalıştırıldı, 2026-08-08):**

- Backend: **657/657 test geçti**, 0 hata, 0 atlanan (`.venv/Scripts/python.exe -m pytest -q`, exit 0; nokta sayımı 657, `F/E/s/x` sayımı 0). Çalışma süresi ~10 dk (Testcontainers ile gerçek PostgreSQL + Mosquitto ayağa kaldırıyor).
- Frontend: **214/214 test geçti, 62 dosya** (`npm test` → `Test Files 62 passed (62) / Tests 214 passed (214)`, 66.8 sn).
- `ruff check backend edge` → `All checks passed!`; `ruff format --check` → `380 files already formatted`; `mypy` (strict) → `Success: no issues found in 258 source files`.
- `tsc --noEmit` (strict) ve `eslint .` → çıktı yok (temiz). `vite build` → `✓ built in 9.53s` (uyarı: antd ve echarts chunk'ları 1.2 MB / 1.0 MB — kod bölme yapılmamış).
- **TODO/FIXME/HACK sayısı: 0.** (`grep -rInE "TODO|FIXME|HACK|XXX"` uygulama kaynağında yalnız 2 isabet veriyor, ikisi de kurtarma kodu biçimini anlatan `XXXX-XXXX` metni: `backend/app/core/security/totp.py:62`, `backend/app/kimlik/schemas.py:27`.)
- Uygulama yerelde ayağa kalkıyor ve demo verisiyle **canlı doğrulandı** (bkz. §7).

**Yarım kalmış / eksik olanlar:**

- **S25 (tedarik zinciri) tasarım aşamasında, kod yok.** `docs/adr/0024-tedarik-zinciri-derinlesmesi.md` yazılmış, `docs/yol-haritasi.md:43` S25'i `⬜` işaretliyor, `backend/app/modules/` altında depo/sayım/satınalma-siparişi paketi yok. Dal `feat/s25-tedarik-zinciri` `main` ile aynı commit'te (`git rev-parse main HEAD` eşit).
- **CI dosyası var, son çalıştırma durumu BİLİNMİYOR.** `.github/workflows/ci.yml` (backend: ruff+mypy+pytest servisli; frontend: eslint+prettier+tsc+vitest+build) — ama 2026-06-30'dan (`ff3335e`) beri dokunulmamış ve `gh` CLI kurulu olmadığı için gerçek run sonucu görülemedi. Dosyanın kendi notu: "Güvenlik (pip-audit/bandit), Playwright E2E, build ve deploy adımları sonraki sprintlerde eklenecek."
- **E2E kapsamı tek dosya:** `frontend/e2e/gercekzaman.spec.ts` (Playwright). Ayakta yığın + seed'li tenant ister; bu oturumda çalıştırılmadı.
- **`REFACTOR-BACKLOG.md`'de 2 açık borç** (82 satır): (1) `duzeltme` stok hareketi mutlak değer yazıyor, sayımı sessizce bozabilir — Sprint 9'a ertelendi, ara koruma `90f374f`'te eklendi; (2) KVKK anonimleştirmesi ile yasal saklama yükümlülüğü çakışması, S29 sonrasına bırakıldı.
- **README güncelliği kaybetmiş.** README sprint tablosu S-VB'yi "▶ sıradaki" gösteriyor (`README.md:53`) ama S-VB (`a3e6b1a`), S24 (`e28156c`) ve S23 (`9eb60ef`) commit'lenmiş. README ayrıca "22 iş modülü" diyor; entitlement kataloğunda **19** lisanslanabilir modül var (`MODUL_KATALOGU` uzunluğu), Python paketi olarak 27 modül klasörü var. Doğru sayı bağlama göre 19 veya 27; 22 hiçbirini karşılamıyor.
- **Üretim dağıtımı yok.** `infra/` altında yalnızca `mosquitto.conf` var; Kubernetes/Terraform/deploy betiği yok. `docker-compose.yml` geliştirme yığını (Traefik dev panosuyla).

---

## 3. Problem

### README/PRODUCT.md'nin anlattığı problem

Bir fabrikada üretim gerçeği (makine ne yapıyor, ne kadar duruyor, OEE ne) sahada; iş verisi (iş emri, stok, kalite, bakım, personel) ayrı tablolarda ve ayrı yazılımlarda duruyor. Operatör bir arızayı görüp aksiyona dönüştürmek için ekran değiştirmek zorunda; yönetici tesisin durumunu görmek için dağınık tabloları birleştiriyor. Hedef: "operatör bir olayı saniyeler içinde görüp aksiyona dönüştürür; yönetici dağınık tablolar yerine tek panodan tesisi yönetir" (`PRODUCT.md`).

Mevcut çözümlerin neden yetmediğine dair **kodda veya dokümanda gerekçeli bir rakip analizi yok** — README yalnızca "modül modül lisanslanabilir" ve "KVKK uyumlu" diyor. Bunlar iddia, kanıt değil. `PRODUCT.md`'nin "Anti-references" bölümü rakip *yazılımları* değil, rakip *görsel dilleri* reddediyor ("SaaS-cream/aydınlık-pastel yönetim paneli", "temasız Ant Design").

### Kodun anlattığı problem (doğrulanmış)

Kod, README'den **daha dar ve daha spesifik** bir problemi çözüyor; ayrışma var ve **kod daha güncel**:

1. **Sahadan otomatik veri toplama gerçekten çalışıyor** ve elle giriş varsayımını ortadan kaldırıyor: `edge/` bağımsız bir Python paketi (sürücü + store-and-forward tamponu + MQTT yayıncısı), `backend/app/ingestion/` MQTT'den tenant şemasına idempotent yazıyor, `uretim_verileri` TimescaleDB hypertable'ı, sonuç WebSocket ile panoya düşüyor. Bu, README'nin en somut iddiası ve karşılığı var.
2. **Asıl mühendislik ağırlığı "çok kiracılı SaaS olarak satılabilirlik"e gitmiş**, MES/ERP fonksiyonuna değil. `backend/app/modules/` altındaki 27 paketin 4'ü (`abonelik`, `entegrasyon`, `dis`, `uyum`) doğrudan lisanslama/entegrasyon/uyum işidir; bunlara `app/platform/` ve `app/control_plane/` iki üst düzey paketi eklenir. Commit tarafında da benzer: abonelik/entitlement, platform admin, webhook/dış portal, güvenlik & uyum konularını anan commit'ler **172'nin 62'si (~%36)** (`git log --grep="s16\|s17\|s18\|s23\|sso\|2fa\|uyum\|kvkk\|abonelik\|entitlement\|platform\|webhook\|dis-portal" -i \| wc -l`; kaba filtre, yanlış pozitif içerebilir). Yani ürünün ayırt edici tarafı "fabrika yazılımı" değil, **"fabrika yazılımını çok kiracılı, modül modül lisanslanabilir, KVKK/ISO 27001 denetlenebilir bir SaaS olarak paketleme"** — README bunu bir madde olarak geçiyor, kod bunu merkeze koyuyor.
3. **KVKK bir özellik değil, kısıt olarak koda gömülü**: TC kimlik maskeleme sunucu tarafında, `ik:oku` erişim kısıtı, tam-şema veri ihracı + otomatik imha + indirme denetimi (`e5b1c7d4a238` migration, `docs/uyum/kisisel-veri-envanteri.md`). Bu, "Türkiye'de satılacak" varsayımının mimari sonucu.

---

## 4. Sistem

### Ana bileşenler ve sorumluluk sınırları

| Bileşen | Sorumluluk sınırı | Kaynak |
|---|---|---|
| **React SPA** (`frontend/src`) | Tek uygulama, **üç ayrı düzlem** barındırıyor: tenant uygulaması (kabuklu, menü RBAC + entitlement süzgeçli), `/platform` (ayrı store, ayrı istemci, `X-Tenant` göndermez, ayrı refresh anahtarı), `/kiosk` + `/dis` (kabuksuz). 54 rota tanımı, 32 modül klasörü. | `frontend/src/App.tsx` (`path="..."` sayımı 54), `frontend/src/modules/` |
| **FastAPI monolit** (`backend/app`) | Tüm iş mantığı tek süreçte: 27 modül router'ı + kimlik + platform + control_plane + ingestion. **182 OpenAPI yolu / 241 operasyon / 380 şema.** | `create_app().openapi()` çıktısı, `backend/app/modules/` |
| **`core/db/tenancy.py`** | Tenant izolasyonunun **tek savunma hattı** (RLS bilinçli olarak kapsam dışı, ADR-0003). `set_config('search_path', ..., is_local=true)` + slug doğrulama + `after_begin` oturum kancası. Bu dosya yanlışsa veri sızar; başka katman yakalamaz. | `backend/app/core/db/tenancy.py:1-11` (dosya kendi başlığında "EN KRİTİK modül" diyor) |
| **PostgreSQL 16 + TimescaleDB** | `public` şeması (8 tablo: tenant, abonelik, plan, platform yöneticisi, platform denetim izi, tenant ihraçları…) + her kiracı için `tenant_<slug>` şeması (**50 tablo**). Zaman serileri hypertable + continuous aggregate. Dev veritabanında şu an 9 tenant şeması var. | `tenant_metadata.tables`=50, `public_metadata.tables`=8; `psql` şema listesi |
| **Redis** | Üç iş: WebSocket için pub/sub kanalları (`tenant:<slug>:olaylar`), refresh token iptal listesi, rate limit sayacı. Kalıcı veri tutmaz. | `README.md` mimari özeti, `backend/app/core/security/` |
| **MinIO (S3)** | Üç tür artefakt, hepsi tenant-önekli anahtarla: DYS belge sürümleri (`tenant_<slug>/belge/...`), async raporlar (`tenant_<slug>/rapor/...`), KVKK ihraç ZIP'leri (`platform/ihrac/...`). | `docker-compose.yml`, S12/S14/S17 commit'leri |
| **Edge Gateway Agent** (`edge/`) | Backend'den **bağımsız paket**: sürücü katmanı (simülatör çalışır, OPC-UA/Modbus iskelet), bağlantı koptuğunda store-and-forward tamponu, MQTT'ye yayın. Buluta hiç HTTP çağrısı yapmaz. | `edge/`, ADR-0010 |
| **Ingestion Worker** | Ayrı compose servisi (`ingestion`). MQTT'ye abone olur, mesajı doğrular, tenant şemasına **idempotent** yazar. Hata izolasyonu mesaj başına. | `docker-compose.yml:29`, `backend/app/ingestion/` |
| **Webhook Relay** | **Ayrı süreç** (`backend/scripts/webhook_relay.py --tek-tur`). Outbox tablosundan (`giden_olaylar`) okur, HMAC imzalar (Stripe deseni `t=..,v1=..`), 1dk→6sa backoff ile 6 deneme yapar. API süreci içinde koşmaz. | `backend/scripts/webhook_relay.py`, ADR-0020 |

### Veri akışı

1. **Girdi — saha:** PLC/simülatör → Edge Agent (store-and-forward tamponu) → MQTT `mqtt` broker → Ingestion Worker → `tenant_<slug>.uretim_verileri` (hypertable).
2. **Girdi — kullanıcı:** SPA → FastAPI → `tenant_cozumle` dependency (subdomain veya `X-Tenant` başlığı → doğrulama → `search_path`) → modül servisi → tenant şeması.
3. **Girdi — dış sistem:** API anahtarı (`fos_`, SHA-256 özet + kapsam beyaz listesi) ile `X-API-Anahtar` başlığı → salt-okunur `/entegrasyon/*`; ve firma-kapsamlı dış portal `/dis/*`.
4. **Durma noktası:** PostgreSQL (ilişkisel + zaman serisi), MinIO (ikili artefakt), Redis (geçici).
5. **Çıkış — canlı:** domain olayı → `giden_olaylar` outbox → (a) Redis pub/sub → WebSocket → tarayıcıda anlık invalidate; (b) Webhook Relay → imzalı HTTP POST → müşteri sistemi.
6. **Çıkış — dosya:** async rapor görevi → PDF (ReportLab) / XLSX (openpyxl) → MinIO → 409-korumalı indirme ucu. KVKK ihracı: `information_schema` keşfiyle tam şema dump → ZIP → MinIO.

### Dış bağımlılıklar

PostgreSQL 16 + TimescaleDB eklentisi · Redis 7 · MinIO · Mosquitto (MQTT) · Traefik (yalnız dev yönlendirme) · scikit-learn/joblib (yerel model artefaktları; harici ML servisi **yok**) · OIDC sağlayıcı (S23 SSO; testlerde sahte IdP, gerçek IdP ile denenmedi). **Ödeme sağlayıcısı yok** — abonelik/plan tamamen kendi tablolarında, Stripe yalnız webhook imza *deseni* olarak taklit edilmiş, entegrasyon değil.

### Diyagram için önerilen kutular (9 kutu)

```
[1] Tarayıcı SPA (React) ──HTTP/WS──> [2] FastAPI Monolit
                                            │
        ┌───────────────────┬───────────────┼───────────────┬──────────────────┐
        ▼                   ▼               ▼               ▼                  ▼
 [3] PostgreSQL 16     [4] Redis      [5] MinIO (S3)   [9] Webhook Relay ──> dış sistem
   + TimescaleDB      pub/sub +        belge/rapor/      (ayrı süreç)
  public + tenant_*   iptal + rate     KVKK ihraç
        ▲
        │
 [8] Ingestion Worker <──[7] MQTT Broker<──[6] Edge Gateway Agent <── PLC / simülatör
```

1. Tarayıcı SPA (React) — üç düzlem: tenant / platform / kiosk-dış
2. FastAPI Monolit — 27 modül, 241 uç
3. PostgreSQL 16 + TimescaleDB — `public` + `tenant_<slug>` şemaları
4. Redis — pub/sub, refresh iptal, rate limit
5. MinIO (S3) — belge sürümü, rapor, KVKK ihracı
6. Edge Gateway Agent — store-and-forward
7. MQTT Broker (Mosquitto)
8. Ingestion Worker — idempotent yazım
9. Webhook Relay — HMAC imzalı, retry'lı (ayrı süreç)

---

## 5. Kritik kararlar

### Karar 1 — Şema-başına-tenant (kiracı başına PostgreSQL şeması)

- **Seçim:** Her kiracı kendi `tenant_<slug>` PostgreSQL şemasında; izolasyon `search_path` ile, işlem-yerel `set_config(..., is_local=true)` kullanılarak. (ADR-0003)
- **Alternatif:** Tek şema + her tabloda `tenant_id` kolonu + PostgreSQL Row-Level Security. Bu, çok kiracılı SaaS'ın varsayılan yoludur ve tek migration ağacı ile çalışır.
- **Gerekçe:** ADR-0003 RLS'i **bilinçli olarak kapsam dışı** bırakıyor. Kod yorumunun kendi ifadesiyle: izolasyon tek savunma hattı olarak tek noktada (`tenancy.py`) çözülmüş; kiracı verisi fiziksel olarak ayrı olduğu için KVKK ihracı ve kiracı silme (`DROP SCHEMA CASCADE`) tek komuta indirgeniyor — S17'nin tam-şema ihracı ve tenant silme özellikleri bu karar olmadan yazılamazdı.
- **Bedel:** Üç somut kayıp. (a) **Migration fan-out zorunluluğu:** iki ayrı Alembic ağacı (`public/` 5, `tenant/` 18 revizyon) ve her tenant şemasında ayrı ayrı koşma; bu, `alembic-fan-out` adında ayrı bir proje disiplini yazılmasını gerektirdi. (b) **Sessiz sürükleme riski:** yeni izin/rol kodları mevcut şemalara kendiliğinden inmiyor — bu gerçekten patladı (§6). (c) **Kiracılar-arası tek sorgu imkânsız:** platform panelinde "tüm tenant'larda toplam X" gibi bir soruyu tek `SELECT` ile cevaplayamazsınız, şema şema dolaşmak gerekir (`duzeltme_denetimi.py` tam olarak bunu yapıyor: 9 şemayı sırayla tarıyor).

### Karar 2 — Modüler monolit (mikroservis değil)

- **Seçim:** 27 iş modülü tek FastAPI süreci içinde paket sınırlarıyla ayrılmış; ingestion ve webhook relay yalnızca **iki** işlem dışarı alınmış. (ADR-0002)
- **Alternatif:** Modül başına servis (üretim servisi, stok servisi, kalite servisi…) + servisler arası olay/HTTP.
- **Gerekçe:** Tek geliştirici, 33 günlük takvim, 15 aktif gün. Ortak çekirdek (tenant çözümleme, RBAC, outbox, denetim izi) tek yerde durursa her modül onu ücretsiz devralıyor — nitekim S9'un `FOR UPDATE` serileştirmesi S16'nın koltuk limitinde, S3'ün `oee_hesapla` saf çekirdeği S14 analitiğinde ve S15 dijital ikizinde yeniden kullanıldı.
- **Bedel:** (a) Modül sınırları **yalnızca disiplinle** korunuyor; derleyici veya ağ sınırı zorlamıyor — bir modülün diğerinin servisini doğrudan import etmesini engelleyen bir mekanizma yok. (b) Ölçekleme bütünsel: stok modülü ağır sorgu atarsa aynı süreçteki WebSocket bağlantıları da etkilenir. (c) `backend/app/api/router.py` 31 kez değişmiş (en çok değişen dosya) — her yeni modül tek bir merkezî dosyaya dokunuyor, bu bir birleştirme sıcak noktası. (d) Tek dilde kilitli: ML tarafı ayrı bir Python servisi olsaydı bağımsız ölçeklenebilirdi, şu an API sürecinin belleğinde.

### Karar 3 — Entitlement (modül lisansı) her istekte veritabanından, önbelleksiz

- **Seçim:** `modul_gerekli("stok")` dependency'si her korumalı istekte plan + kiracı hak haritasını **veritabanından** okuyor; sonuç önbelleğe alınmıyor, JWT claim'ine gömülmüyor. Admin bypass'ı da yok — modül kapalıysa admin de 403 `MODUL_KAPALI` alır. (ADR-0018)
- **Alternatif:** Entitlement'ı giriş anında JWT'ye claim olarak yazmak veya Redis'te TTL'li önbelleğe almak. Her ikisi de tek DB sorgusuna indirirdi.
- **Gerekçe:** Platform yöneticisi paneldeki matristen bir modülü kapattığında etkinin **anında** olması isteniyor; token ömrü kadar veya TTL kadar gecikme, "aboneliği askıya aldım ama hâlâ kullanıyor" durumunu yaratır. S17'de tenant askıya alma da aynı sözleşmeyi kullanıyor.
- **Bedel:** Her entitlement-korumalı istekte **iki ek veritabanı sorgusu** (`plan_getir` + `hak_haritasi_getir`, `entitlement_service.py:49-55`), ve bu 19 router'a bağlı. Yani platformun en sık çalışan kod yolu, en çok ölçeklenmesi gereken yerde önbelleksiz. Şu anki veri hacminde ölçülebilir bir sorun **görülmedi**, ama ölçüm de yapılmadı — bu bir gelecek borcu, `REFACTOR-BACKLOG.md`'de kaydı yok.

### Karar 4 — Türkçe tanımlayıcı standardı (tablo, kolon, rota, DTO alanı, sınıf adı)

- **Seçim:** Kod içindeki her isim Türkçe: tablolar (`uretim_verileri`, `giden_olaylar`, `platform_denetim_izi`), rotalar (`/makineler`, `/satinalma-talepleri`, `/kimlik/token`), sınıflar (`YetkiHatasi`, `BellekNesneDepo`), yanıt zarfı alanları (`hata_kodu`, `detaylar`). Bunun için ayrı bir proje standardı yazılmış (`turkce-identifier-standardi`).
- **Alternatif:** İngilizce tanımlayıcılar + yalnızca kullanıcıya görünen metinlerde i18n (endüstri varsayılanı).
- **Gerekçe:** Alan dili Türkçe (irsaliye, zimmet, fazla mesai, uygunsuzluk, KVKK terimleri). İngilizceye çevirmek terim kaybı yaratıyor — "uygunsuzluk" ≠ "nonconformity" tam karşılığı değil, "zimmet" için tek kelimelik karşılık yok. Ekip Türkçe konuşuyor, müşteri Türkçe.
- **Bedel:** (a) **Karışık dil kaçınılmaz:** framework/kütüphane API'leri İngilizce olduğu için her dosyada iki dil yan yana (`async def kontrol(tenant: Annotated[Tenant, Depends(tenant_cozumle)])`). (b) **Türkçe karakter tuzağı gerçek maliyet çıkardı:** noktalı `İ` regex ve büyük/küçük harf dönüşümlerinde ayrı bir hata kaynağı oldu (proje derslerinde kayıtlı). (c) Türkçe bilmeyen bir katkıcı için giriş bariyeri; açık kaynağa çevrilirse yeniden adlandırma maliyeti tüm kod tabanına yayılır. (d) OpenAPI çıktısı Türkçe olduğu için üretilen TypeScript tipleri de Türkçe — ve S17'de bu **çakışma** üretti: platform DTO'ları `Platform*` önekiyle yeniden adlandırılmak zorunda kaldı, aksi hâlde `openapi-typescript` ad çakışmasıyla frontend'i kırıyordu.

---

## 6. Zorlandığım yer

Üç gerçek olay var. Birincisi en öğreticisi olduğu için tam anlatılmış; diğer ikisi kısa.

### 6.1 (Birincil) İzin kataloğu ile kiracı şemaları arasında sessiz sürükleme

**Nasıl fark edildi.** Her sprint izin kataloğuna yeni kod ekliyor (S16 modül hakları, S23 `denetim:oku` + `kvkk:yonet`, S25 `stok:duzeltme`). Belirti: yeni yazılan uç, **var olan** bir kiracıda 403 dönüyordu; rol yönetimi matrisinde satır eksik görünüyordu. Yeni açılan kiracılarda aynı uç sorunsuz çalıştığı için hata "bende çalışıyor" sınıfına giriyordu. İki sprint boyunca bu, canlı kiracıları elle yeniden provizyonlayarak kapatıldı. Commit gövdesindeki tespit: *"İki sprinttir bu elle yeniden provizyonlamayla kapatılıyordu; elle adım kaçınılmaz olarak unutulur."*

**Kök sebep.** Yanlış varsayım şuydu: *"İzin kataloğu kodda tek yerde tanımlı olduğuna göre, kod güncellenince her yerde geçerlidir."* Değil. İzinler kiracı şemasındaki `izin` tablosuna **provizyon anında bir kez** yazılıyordu. Şema-başına-tenant kararı (Karar 1) veriyi N kopya hâline getirdiği için, kodda tek olan katalog veritabanında N tane bağımsız kopyaya karşılık geliyordu ve migration fan-out'u yalnızca **yapıyı** taşıyordu, **tohum verisini** değil. Yani bu, Karar 1'in doğrudan faturasıydı.

**Nasıl çözüldü** (`78a1e37`, 2026-07-30):

- `backend/app/control_plane/uzlastirma.py` (132 satır) katalog ile şema arasındaki farkı kapatıyor ve **migration fan-out'unun ardından kendiliğinden** koşuyor (`tenant_yukselt_tum(uzlastir=True)`).
- Provizyon yolu da aynı fonksiyonu çağırıyor — tek doğruluk kaynağı. Ayrışsalardı yeni kiracı ile eskiler arasında yine fark oluşurdu; commit gövdesi bu tuzağı açıkça not ediyor.
- **Yalnızca eklemeli:** katalogda olmayan izin/rol silinmiyor (elle tanımlanmış kayıtlar korunuyor). Varsayılan rollerin izin kümesi katalogla eşitleniyor — bu, "roller bugün API'den düzenlenemiyor, dolayısıyla üzerine yazılacak kullanıcı emeği yok" gerekçesine dayanıyor ve gerekçe kodda notlandı ("roller düzenlenebilir olursa bu karar yeniden ele alınmalı").
- Elle onarım için `backend/scripts/izin_uzlastir.py` (`--kuru` ile yalnız rapor).
- **Kalıcı sözleşme testi:** hiçbir kiracıda katalog izni eksik olamaz (`backend/tests/test_izin_uzlastirma.py`, 135 satır; onarım, idempotentlik, katalog dışı kayıtların korunması ve rol kümesi eşitlemesi ayrı ayrı testli).

**Sonrasında ne değişti.** Dev veritabanında doğrulandı: `s12live`…`s18live` kiracılarının **hiçbiri** S23 izinlerini almamıştı (yalnız `demo` elle düzeltilmişti); uzlaştırma sonrası kuru rapor "eksik yok" verdi. Etkisi bir sonraki sprintte hemen görüldü: `90f374f`'te yeni eklenen `stok:duzeltme` izni için commit gövdesi *"Yeni izin, S23 uzlaştırması sayesinde mevcut tenant'lara kendiliğinden inecek"* diyor — yani elle adım listeden tamamen kalktı. Daha genel ders: şema-başına-tenant'ta **yapı migration'ı yeterli değil, tohum verisi için de bir uzlaştırma mekanizması gerekiyor** ve bu mekanizma fan-out'a bağlı olmalı, insan hafızasına değil.

### 6.2 (İkincil) İzolasyonu güvenli kılan tercih, istek ortasında commit edildiğinde izolasyonu bozuyordu

`search_path` bilinçli olarak **işlem-yerel** (`set_config(..., is_local=true)`) ayarlanmıştı; gerekçe sağlamdı: bağlantı havuza dönerken ayar sızmasın. Varsayım şuydu ki bu her durumda güvenli. Değildi — istek **ortasında** commit eden bir uç (async görev tetikleme, KVKK imhası, rapor kuyruğa alma), commit sonrası sorgularını şemasız çalıştırıyordu; o sorgular ya hata veriyor ya da `public`e düşerek **yanlış veriye dokunuyordu**. Bu bir tenant izolasyonu riski.

Bir üretim olayıyla değil, S25 öncesi kendi kod incelemesinde bulundu ("İNCELEME MADDESİ 3"). Tüm `.commit()` çağrıları tarandı; risk sınıflandırıldı (AI/rapor/KVKK-ihraç uçları yanıt DTO'sunu commit öncesi anlık görüntülüyor ve sonrasında sorgu yok → yapısal olarak güvenli; arka plan görevleri kendi oturumunda şema-nitelikli SQL kullanıyor; platform ucu zaten `public`). **Gerçek risk yalnız KVKK imha yolundaydı.**

Çözüm (`90f374f`, 2026-07-31): "commit'ten sonra elle kurmayı hatırlama" gereksinimini kaldıran bir `after_begin` SQLAlchemy oturum kancası — doğrulanmış tenant bağlamı varsa her yeni işlemde `search_path` yeniden kuruluyor (`backend/app/core/db/tenancy.py:80`, gerekçe yorumu 56-67. satırlarda). Kancadaki güvenlik inceliği ayrıca testle korunuyor: kanca **ham `X-Tenant` başlığını değil**, `tenant_cozumle`'nin doğrulamadan geçirip set ettiği `cozulmus_tenant_ctx`'i okuyor — aksi hâlde istemci başlıkla istediği şemayı seçtirebilirdi. Regresyon testi: `backend/tests/test_search_path_commit_korumasi.py` (103 satır).

### 6.3 (Üçüncül) Alembic, kiracı provizyonundan sonra API'nin loglarını kalıcı olarak susturuyordu

Her iki `env.py` de `fileConfig`'i varsayılan `disable_existing_loggers=True` ile çağırıyordu. Migration **süreç içinde de** koşuyor (S17'nin senkron tenant provizyonu, testlerdeki fan-out) — bu yüzden platform panelinden bir kiracı provizyonlandıktan sonra, API sürecinde `alembic.ini`'de adı geçmeyen **tüm** `app.*` logger'ları kapanıyordu: denetim, SSO debug ve hata izi logları sessizce kayboluyordu. Yani sistem çalışmaya devam ediyor, sadece görünmez oluyordu — bu yüzden fark edilmesi zor.

Düzeltme `ee0c175` (2026-07-30): iki `env.py`'de `disable_existing_loggers=False` + gerekçeyi anlatan yorum. Regresyon testi `test_provizyon_uygulama_loglarini_susturmaz` (`backend/tests/test_s2_provizyon.py`), commit gövdesindeki nota göre düzeltme geri alınınca kırmızıya döndüğü **doğrulanmış**.

---

## 7. Ekran görüntüsü hazırlığı

### Yerelde ayağa kalkıyor mu? — **Evet, bu oturumda denendi ve kalktı.**

Ölçülen komut zinciri (Windows, repo kökünden):

```bash
# 1) Altyapı
docker compose up -d db redis minio          # timescale/pg16 + redis + minio
#    (MQTT/edge akışı isteniyorsa ek olarak: docker compose up -d mqtt ingestion)

# 2) Backend — MUTLAKA repo kökünden (pydantic .env'i çalışma dizinine göre arar)
./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 3) Frontend
cd frontend && npm install && npm run dev     # http://localhost:5173
```

**Doğrulanan sonuç (2026-08-08):**

- `GET /saglik` → `HTTP 200`, `{"durum":"ayakta","uygulama":"FabrikaOS","surum":"0.1.0","ortam":"dev"}`
- `POST /api/v1/kimlik/token` (`X-Tenant: demo`, `admin@demo.test` / `[GİZLİ — yerel demo parolası, README.md'de]`) → geçerli JWT
- `GET /api/v1/uretim/ozet` → `HTTP 200`, gerçek seed verisi: 13 makine, 10 çalışıyor / 1 durdu / 1 bakımda / 1 arızalı, ortalama OEE **0.773**
- `GET /api/v1/makineler` → `LAZER-1 Fiber Lazer Kesim 1`, `ABKANT-1 Abkant Pres Büküm` … (dolu)
- `npm run build` → `✓ built in 9.53s`

**Frontend tarayıcıda bu oturumda açılmadı** — Vite dev sunucusu başlatılmadı, yalnızca `build`/`typecheck`/`test` çalıştırıldı. Ekran görüntüsü alınacaksa 3. adım ayrıca koşulmalı.

⚠️ İki tuzak (proje derslerinde kayıtlı, hâlâ geçerli):
- Backend **repo kökünden** başlatılmalı; `backend/` içinden başlatılırsa `.env` bulunamaz, `db:5432` varsayılanına düşer ve giriş dahil her istek 500 döner.
- `--reload` bu ortamda çalışmıyor (watchfiles yok) → backend değişikliğinde uvicorn elle yeniden başlatılmalı.

### Ön koşullar

| Koşul | Olmadan ne olur |
|---|---|
| **PostgreSQL 16 + TimescaleDB eklentisi** | Uygulama açılmaz. Eklenti şart: `create_hypertable` çağrıları migration'da. Düz `postgres:16` imajı yetmez. |
| **Migration koşulmuş olması** | `python -m alembic --name public upgrade head` **ve** `--name tenant upgrade head`. Fan-out olmadan kiracı şeması boş. |
| **Redis** | Giriş akışı kırılır (refresh iptal listesi + rate limit) ve WebSocket canlı güncelleme çalışmaz. |
| **MinIO** | Uygulama açılır, ama DYS belge yükleme/indirme, async rapor indirme ve KVKK ihracı 5xx verir. |
| **`.env`** | `.env.example`'dan kopyalanmalı. `SECRET_KEY` üretimde değiştirilmezse `APP_ENV=prod`'da kod bilerek reddediyor (`ff3335e` "prod secret koruması"). |
| **MQTT + ingestion** | Yalnız saha/edge akışı için. Olmadan uygulama tam çalışır, sadece canlı makine verisi akmaz. |
| **Ödeme sağlayıcı anahtarı** | **Gerekmiyor** — ödeme entegrasyonu yok. |
| **OIDC sağlayıcı** | Yalnız SSO ile giriş denenecekse. Parola girişi bağımsız çalışır. |

### Demo veri — **var ve çalışır durumda**

`backend/scripts/demo_verisi.py` (846 satır) tüm modülleri gerçekçi veriyle dolduruyor. Veriyi doğrudan DB'ye değil **API üzerinden** giriyor; böylece iş kuralları (stok bakiyesi, durum makineleri, OEE, outbox olayları, MinIO nesne yazımı) gerçek akışla çalışıyor. `random.Random(42)` ile tohumlu → tekrarlanabilir.

```bash
./.venv/Scripts/python.exe backend/scripts/demo_verisi.py --tenant demo
```

Aynı kiracıya ikinci kez çalıştırma kayıtları çoğaltır; betik bunu fark edip durur (`--force` ile devam eder). Temiz demo için yeni slug verilmeli.

**Mevcut durum:** dev veritabanında `tenant_demo` **zaten seed'li ve ayakta** (yukarıdaki canlı çağrılarla doğrulandı). Ayrıca 8 eski test kiracısı duruyor: `s9live`, `s11live`…`s18live`.

**Demo hesapları** — 8 rol, hepsi ortak bir yerel parola (`[GİZLİ]` — değer `README.md`'nin "Demo tenant" bölümünde, üretime taşınmaz): `admin@demo.test` (tam yetki), `uretim.sefi@demo.test` (izleyici), `depo@demo.test`, `satinalma.onay@demo.test`, `kalite@demo.test`, `ik@demo.test`, `ik.yonetici@demo.test`, `crm@demo.test`. Giriş ekranında "Firma kodu" = `demo` yazılmalı (localhost'ta subdomain yok). Platform düzlemi ayrı: `/platform` → `root@fabrikaos.test` / `[GİZLİ]`.

### Ekran görüntüsü alınabilecek anlamlı ekranlar (6)

| # | Rota | Neden önemli — hangi iddiayı kanıtlıyor |
|---|---|---|
| 1 | `/ikiz` — Dijital İkiz | Ürünün imza ekranı ve en görsel kanıtı: elle yazılmış SVG tesis şeması, makine durumu canlı LED olarak yanıyor, düzenleme modunda sürükle-yerleştir + palet. "Sahadan canlı veri" iddiasını tek karede gösteriyor. |
| 2 | `/pano` — 360° Yönetim Panosu | Rol/persona bazlı pano, masonry düzen, KPI şeridi + canlı OEE + uyarı akışı. "Yönetici tek panodan tesisi yönetir" iddiasının doğrudan karşılığı. ECharts grafikler dolu (13 makine, OEE 0.773). |
| 3 | `/abonelik` — Abonelik & Modüller | Portföy açısından en ayırt edici ekran: bunun bir *SaaS ürünü* olduğunu kanıtlıyor. Koltuk limiti progress bar'ı + modül×plan hak matrisi (hat renkli) + deneysel özellik rozeti. Kapalı bir modüle gidildiğinde çıkan upsell ekranı (`/tahminler`) ikinci kare olarak eşleştirilebilir. |
| 4 | `/platform/tenantlar/:id` — Platform Admin, kiracı detayı | Ayrık control-plane düzlemi: turuncu hat rengi + PLATFORM filigranı ile görsel olarak ayrışıyor. Entitlement switch matrisi, slug yazarak onay isteyen tehlike modalı, KVKK ihraç ZIP indirme. Çok kiracılı mimariyi *gösterilebilir* kılan tek ekran. |
| 5 | `/uygunsuzluklar` veya `/is-emirleri` (detay çekmecesi açık) | Durum makinesi + onay akışı derinliği: 6 aşamalı CAPA veya iş emri durum geçişi, KPI şeridi + durum zaman çizelgesi olan detay çekmecesi. "Sadece liste ekranı değil, gerçek iş akışı" iddiasını kanıtlıyor. |
| 6 | `/kiosk` — Kabuksuz büyük ekran | Kontrast: aynı veri, sıfır buton, sıfır menü, salt-okunur. Persona düşünülmüş bir ürün olduğunu tek karede anlatıyor. Ekran görüntüsü için 1920×1080 idealdir. |

Alternatif/yedek: `/webhooklar` (3 sekme: abonelikler / teslimat günlüğü / API anahtarları) — dış entegrasyon iddiasını kanıtlar; `/dis` (müşteri portali, kabuksuz).

### Gerçek veri riski — **düşük, ama iki uyarı var**

Seed verisi tamamen sentetik ve bunu doğruladım:
- TC kimlik numaraları desen üretimi: `f"1000000{i:02d}46"` (`demo_verisi.py:545`) — geçerli TC algoritmasına uymaz.
- E-postalar `@demo.test` ve `.example` alan adları (RFC 2606 ayrılmış test alanları), telefonlar `0532 000 00 XX` / `0212 000 00 00`.
- Kişi adları yaygın Türkçe adlar (Mehmet Yılmaz, Ayşe Demir…) — kurgusal.
- Ayrıca TC numarası **sunucu tarafında maskeleniyor**: ekranda `*********01` görünüyor, `ik:oku` izni olmayan hiç göremiyor. Yani ekran görüntüsünde ham TC çıkması teknik olarak da mümkün değil.

⚠️ **Uyarı 1:** Seed'deki firma adlarından bazıları gerçek Türk şirketlerini çağrıştırıyor: "Aksa Makina San. A.Ş.", "Nova Beyaz Eşya A.Ş.", "Marmara Savunma Teknolojileri", "Demir Çelik Ltd. Şti." (`demo_verisi.py:641-647`). Hiçbiri gerçek bir müşteri değil, ama "Aksa" ve savunma sanayi çağrışımı yayında yanlış anlaşılabilir. Ekran görüntüsü almadan önce bu 6 adı nötr kurgusal adlarla değiştirmek ucuz bir sigorta.

⚠️ **Uyarı 2:** Demo hesap parolaları `README.md`'de açıkça yazılı (bu brifingde `[GİZLİ]`) ve giriş formu ekran görüntüsüne girerse görünebilir. Yalnız yerel ortam için; ama "bu bir demo hesabıdır" notu olmadan yayımlanırsa gerçek kimlik bilgisi sanılabilir.

---

## 8. Ölçülebilir ne varsa

Aşağıdaki her satır **bu oturumda çalıştırılmış** komut çıktısına veya doğrudan dosya sayımına dayanıyor. Tahmin yok.

| Ölçüm | Değer | Kanıt |
|---|---|---|
| Backend test sayısı ve sonucu | **657 / 657 geçti**, 0 hata, 0 atlanan | `pytest -q` exit 0; çıktı dosyasında 657 nokta, 0 adet `F/E/s/x` |
| Frontend test sayısı ve sonucu | **214 / 214 geçti**, 62 dosya, 66.8 sn | `npm test` → `Test Files 62 passed (62) / Tests 214 passed (214)` |
| Test kodu hacmi | BE 14.441 satır + FE 3.966 satır = **18.407 satır** (elle yazılmış kodun **%23.5**'i) | `git ls-files "backend/tests/*.py" ... \| wc -l` |
| Backend lint | **temiz** — `All checks passed!` | `ruff check backend edge` |
| Backend biçim | **temiz** — `380 files already formatted` | `ruff format --check backend edge` |
| Backend tip kontrolü | **temiz (strict)** — `Success: no issues found in 258 source files` | `mypy` (`pyproject.toml`: `strict = true`) |
| Frontend tip kontrolü | **temiz (strict)** — çıktı yok | `tsc --noEmit` |
| Frontend lint | **temiz** — çıktı yok | `eslint .` |
| Üretim derlemesi | **başarılı**, 9.53 sn | `vite build` → `✓ built in 9.53s` |
| Derleme uyarısı | antd chunk **1.272 MB** (gzip 396 kB), echarts chunk **1.035 MB** (gzip 343 kB) — kod bölme yapılmamış | aynı çıktı |
| TODO / FIXME / HACK sayısı | **0** (2 isabetin ikisi de `XXXX-XXXX` biçim metni) | `grep -rInE "TODO\|FIXME\|HACK\|XXX"` uygulama kaynağında |
| API yüzeyi | **182 yol / 241 operasyon / 380 şema** | `create_app().openapi()` çıktısından sayım |
| Veritabanı şeması | kiracı başına **50 tablo**, `public` **8 tablo** | `tenant_metadata.tables` / `public_metadata.tables` uzunlukları |
| Migration revizyonu | tenant ağacı **18**, public ağacı **5** (toplam 3.201 satır) | `ls backend/migrations/*/versions/` |
| RBAC kataloğu | **50 izin kodu**, **19 varsayılan rol** | `len(IZIN_KATALOGU)`, `len(VARSAYILAN_ROLLER)` |
| Entitlement kataloğu | **19 lisanslanabilir modül**, 2 özellik bayrağı, 4 plan | `len(MODUL_KATALOGU)`, `len(OZELLIK_KATALOGU)` |
| Python modül paketi | **27** iş modülü klasörü | `ls -d backend/app/modules/*/` |
| Frontend rota tanımı | **54** | `grep -c 'path="' frontend/src/App.tsx` |
| Frontend modül klasörü | **32** | `ls frontend/src/modules/` |
| Canlı OEE (demo tenant) | **0.773** ortalama, 13 makine (10 çalışıyor / 1 durdu / 1 bakımda / 1 arızalı) | `GET /api/v1/uretim/ozet` canlı yanıtı |
| Dev veritabanındaki kiracı şeması | **9** (`demo` + 8 test kiracısı) | `psql` `pg_namespace` sorgusu |
| Mimari karar kaydı (ADR) | **24 adet** (0001–0024) + şablon | `ls docs/adr/` |
| Dokümantasyon | 57 markdown dosyası / **15.329 satır**; yol haritası 623, UI planı 611, mobil plan 363, veri sözlüğü 329 satır | `wc -l` |
| Toplam commit / katkıcı | **172 commit, 1 katkıcı**, 15 aktif gün | `git rev-list --count`, `git shortlog -sn` |

**Kanıtı olmayan, bu yüzden listelenmeyen ölçümler (portföyde de kullanılmamalı):**

- **Test kapsamı (coverage) yüzdesi — BİLİNMİYOR.** `pytest-cov` bağımlılıklarda yok, `.coverage` üretilmiyor. Test sayısı yüksek ama kapsam ölçülmemiş; ikisi aynı şey değil.
- **CI son çalıştırma durumu — BİLİNMİYOR.** Workflow dosyası var, `gh` CLI kurulu olmadığı için gerçek run geçmişi görülemedi. Ayrıca depo `Scryne/FabrikaOS_v2` GitHub public API'sinde `404` dönüyor → **private**, dışarıdan doğrulanamaz.
- **Performans ölçümü — YOK.** Yük testi, p95 gecikme, sorgu profili hiç alınmamış. Entitlement'ın istek başına 2 ek sorgusu (Karar 3) hiç ölçülmedi.
- **Gerçek kullanıcı / üretim veri hacmi — YOK.** Ürün hiç dağıtılmadı; tüm veri seed. "Kullanıcı sayısı" diye bir şey yok.
- **Playwright E2E sonucu — bu oturumda çalıştırılmadı** (ayakta yığın + seed'li tenant ister). Tek spec dosyası var: `frontend/e2e/gercekzaman.spec.ts`.
- Commit gövdelerinde geçen "canlı e2e 56/56", "tarayıcı 12/12" gibi sayılar **o sprintlerde ölçülmüş** ama bugün yeniden doğrulanmadı; portföyde kullanılacaksa "geliştirme sırasında ölçüldü" diye nitelenmeli.

---

## 9. Yayına çıkarma engelleri

| # | Konu | Durum / karar sende |
|---|---|---|
| 1 | **Lisans: tescilli, LICENSE dosyası yok.** README: *"Tescilli (proprietary) — tüm hakları saklıdır. Bu depo bir portföy/ürün geliştirme çalışmasıdır; harici kullanım/çoğaltma yazılı izne tabidir."* Depo GitHub'da **private** (API `404`). | Kod *parçacığı* portföyde göstermek sorun değil (senin kodun), ama depoyu public'e çevirmek ayrı bir karar. Tescilli kalacaksa portföyde "kaynak kod kapalı, ekran görüntüleri ve mimari anlatım paylaşılıyor" demek gerekir. |
| 2 | **Müşteri işi / NDA: yok.** Katkıcı tek kişi (`git shortlog`), kod tabanında müşteri adı, kurum içi belge veya sözleşme referansı bulunmadı. | Engel yok. |
| 3 | **Gömülü sır: bulunamadı.** `.env` izlenmiyor (`.gitignore`'da), izlenen tek ortam dosyası `.env.example` ve içindeki değerler açıkça yer tutucu (`SECRET_KEY=degistir-bu-degeri-uretimde-rastgele-uzun-bir-deger`, `MINIO_SECRET_KEY=fabrikaos-minio-parola`). `.gitignore` ayrıca `*.pem`, `*.key`, `secrets/` kapatıyor. | Engel yok. **Ama** git *geçmişinde* sır taraması yapılmadı — public'e çevrilecekse `gitleaks`/`trufflehog` ile 172 commit taranmalı. |
| 4 | **Demo parolaları README'de açık yazılı** (bu brifingde bilerek `[GİZLİ]` bırakıldı — tür: yerel demo hesabı parolası). README bunları "yalnızca yerel/demo ortamı içindir; üretimde kullanılmamalıdır" uyarısıyla veriyor. | Gerçek sır değil, ama README public'e açılırsa veya giriş formu ekran görüntüsüne girerse yanlış anlaşılabilir. Portföy metnine kopyalanmamalı. |
| 5 | **Seed firma adları gerçek şirketleri çağrıştırıyor** — "Aksa Makina San. A.Ş.", "Nova Beyaz Eşya A.Ş.", "Marmara Savunma Teknolojileri" (`demo_verisi.py:641-647`). | **Karar senin.** Önerim: ekran görüntüsü almadan önce nötr kurgusal adlara çevirmek (tek dosyada 6 satır). |
| 6 | **Üçüncü parti veri: yok.** Dış API'den çekilmiş veri seti veya lisanslı içerik bulunmadı. Tek istisna harita döşemesi: Leaflet yalnız `frontend/src/modules/ikiz/IkizHarita.tsx` içinde kullanılıyor; döşeme sağlayıcısı OSM ise atıf zorunluluğu var. | Coğrafi harita bileşeni ekran görüntüsüne girecekse atıf şeridinin karede kalmasına dikkat. |
| 7 | **PDF şartname deponun içinde:** `FabrikaOS_Proje_Plani.pdf` izlenen dosya. İçeriği bu brifingde incelenmedi. Eğer üçüncü bir tarafın hazırladığı bir şartname ise fikri mülkiyet sorusu doğurabilir. | **Kontrol et.** Kendi yazdığın plansa engel yok. |
| 8 | **KVKK / kişisel veri:** ürün kişisel veri işliyor (personel TC, sağlık/İSG kaydı, izin talebi) ama tüm demo verisi sentetik (§7). `docs/uyum/kisisel-veri-envanteri.md` mevcut. | Engel yok; aksine portföyde anlatılacak bir güç. |
| 9 | **AI eşli geliştirme görünür.** Commit gövdelerinde `Co-Authored-By: Claude Opus 5 / Claude Fable 5` trailer'ları var. | Sır değil, ama portföy anlatısında bunu gizlemek yerine açıkça söylemek tutarlı olur — commit geçmişi public'e açılırsa zaten görünür. |

---

## Portföy oturumuna notlar

- **`slug` önerisi yok** (bilinçli — portföy oturumunun kararı). `status` alanı için değer: **`geliştirme`**.
- `period` için: `2026-06` → `2026-07` (33 takvim günü, 15 aktif gün, ortasında 14 günlük ara).
- `role` için: tek geliştirici (AI eşli).
- `stack` için önerilen 8 madde: FastAPI · PostgreSQL + TimescaleDB · SQLAlchemy + Alembic · React + TypeScript · Ant Design · Redis · MinIO · MQTT.
- Bu brifingde §6.1 en güçlü anlatı malzemesidir: mimari karar (şema-başına-tenant) → doğrudan sonucu olan bir hata → yapısal çözüm zinciri tam ve commit'lerle kanıtlı. §6.2 ikinci sırada; "izolasyonu güvenli kılan tercihin kendisi izolasyonu bozuyordu" cümlesi tek başına bir vaka çalışması açar.
