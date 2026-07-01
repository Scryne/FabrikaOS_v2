# S10 — Kalite & Enerji · Tasarım (Spec)

> Faz 2 / Sprint S10. Onaylı yol haritası: `docs/yol-haritasi.md` ve `~/.claude/plans/…buzzing-cake.md` §4 (FAZ 2 / S10).
> Bağlayıcı skill'ler: `tenant-rbac-conventions`, `turkce-identifier-standardi`, `alembic-fan-out`.

## 1. Amaç ve Kabul Kriterleri

Kalite (denetim + Tam CAPA yaşam döngüsü) ve Enerji (tüketim zaman serisi + trend) modüllerini çekirdeğin üzerine, **çok-kiracılı + RBAC + canlı** kurmak.

Kabul kriterleri (plandan):
1. **CAPA yaşam döngüsü çalışır** — uygunsuzluk `acik → … → kapandi` akışı; geçersiz geçiş reddedilir; düzeltici/önleyici aksiyonlar kaydedilir.
2. **Enerji trendi doğru toplulaştırılır** — `enerji_tuketim` hypertable üzerinden continuous aggregate ile saatlik/günlük trend.
3. **İlgili izinler uygulanır** — `kalite:oku/yaz`, `enerji:oku/yaz`; yetkisiz rol 403.
4. Ek DoD: tenant izolasyon + RBAC + migration fan-out testleri; **ADR-0012** (Kalite CAPA + Enerji hypertable + continuous aggregate).

## 2. Kapsam Kararları (onaylı)

| Karar | Seçim | Gerekçe |
|---|---|---|
| Kapsam | **Backend + frontend** uçtan uca | S3–S9 ile tutarlı; modül demolanabilir. |
| Kalite derinliği | **Tam CAPA** | Kök-neden aşaması + düzeltici/önleyici aksiyonlar ayrı satır varlıkları + zengin durum makinesi. "CAPA yaşam döngüsü çalışır" kriterini güçlü karşılar. |
| Enerji trend | **Gerçek TimescaleDB continuous aggregate** | S3'te ertelenen işi (ADR-0006) kapatır; okuma hızlı; Timescale'i sergiler. Maliyet: migration'da `autocommit_block`. |
| Enerji modeli | **Makine bağlı + enerji türü + elle giriş** | `UretimVerisi` hypertable deseninin aynısı; `makine_id` nullable = tesis geneli; edge otomasyonu bu sprint dışı (YAGNI). |
| Kalite ↔ OEE | **Ayrı** (KaliteKontrol OEE hattını beslemez) | S3 OEE boru hattı (`UretimVerisi.saglam_adet/toplam_adet`) sabit kalır; kapsam/regresyon kontrolü. |
| Uygunsuzluk kaynağı | **Elle** (kaldı denetim otomatik NC üretmez; opsiyonel FK ile bağlanır) | S9 seam deseni; otomatik tetik ileride eklenebilir (YAGNI). |
| Kalite onay izni | **Yok** (tüm CAPA geçişleri `kalite:yaz`) | Plan §3.3 `kalite:onay` içermiyor; izin icat edilmez. |

### 2.1 İyileştirmeler (bu tasarımda katılan)
- **A — Real-time aggregation:** CAGG `materialized_only=false` (varsayılan) → trend ucu, refresh policy henüz çalışmasa bile son ham veriyi materialized veriyle birleştirip döner. Test/UI güncel görür.
- **B — Günlük rollup CAGG üstünde:** temel CAGG saatlik; `aralik=gun` istenirse trend ucu **CAGG üstünde** `time_bucket('1 day', …)` ile toplar (ham hypertable'ı tekrar taramaz). Tek materialized view, iki granülerlik.
- **C — Aksiyon başına durum:** `CapaAksiyon.durum` (`planlandi|tamamlandi|iptal`) ana uygunsuzluk durumundan bağımsız → aksiyon takibi vaka kapanmadan izlenir.
- **D — Doğrulama sertliği:** beyaz-listeler (`KONTROL_TURLERI`, `KONTROL_SONUCLARI`, `UYGUNSUZLUK_ONEMLERI`, `CAPA_AKSIYON_TURLERI`, `ENERJI_TURLERI`); `tuketim > 0`, `numune_adedi ≥ 0`, `uygunsuz_adet ≥ 0` ve `≤ numune_adedi`; varsa `alt_limit ≤ ust_limit`; geçersiz → 422.
- **E — Append-only ölçüm + soft yaşam:** `enerji_tuketim` append-only (audit/zaman serisi); `kalite_kontrolleri` düzeltilebilir değil (kayıt); uygunsuzluk sert silinmez, `iptal` durumuna geçer.
- **F — Kök-neden geç doldurma:** `Uygunsuzluk.kok_neden` açılışta boş; `kok_neden` durumuna geçişte doldurulur (zorunlu değil ama UI'da bu aşamada istenir).

## 3. Bileşenler ve Topoloji

```
backend/app/modules/kalite/       # YENİ — denetim + Tam CAPA (standart modül)
  ├─ models.py                     # KaliteKontrol, Uygunsuzluk, CapaAksiyon
  ├─ durum.py                      # SAF CAPA durum makinesi (DB'siz, birim testli)
  ├─ birimler.py                   # KONTROL_TURLERI/SONUCLARI, ONEMLER, AKSIYON_TURLERI beyaz-listeleri
  ├─ schemas.py                    # Pydantic DTO'lar
  ├─ repository.py                 # sorgular (getir_kilitli = FOR UPDATE, listele = arama/sıralama/filtre)
  ├─ service.py                    # capa_durum_gecisi, aksiyon ekle/güncelle, oto kod
  └─ router.py                     # /kalite-kontrolleri, /uygunsuzluklar (+/{id}/durum, /{id}/aksiyonlar)
backend/app/modules/enerji/       # YENİ — tüketim hypertable + trend (standart modül)
  ├─ models.py                     # EnerjiTuketim (hypertable)
  ├─ birimler.py                   # ENERJI_TURLERI beyaz-liste
  ├─ schemas.py                    # Pydantic DTO'lar (trend nokta dizisi)
  ├─ repository.py                 # listele (filtre) + trend (CAGG sorgusu)
  ├─ service.py                    # olcum_yaz + realtime yayın
  └─ router.py                     # /enerji-tuketimleri (+/trend)
backend/migrations/tenant/…        # YENİ — 4 kalite/enerji tablosu + hypertable + CAGG (fan-out)
backend/app/kimlik/izinler.py      # enerji:yaz eklenir + 2 yeni varsayılan rol
frontend/src/modules/{kalite,enerji}/   # YENİ — kalite + enerji ekranları
```

### 3.1 Saf CAPA durum makinesi `kalite/durum.py`
İş emri/satınalma `durum.py` deseninin aynısı (GECISLER tablosu + `gecis_gecerli_mi` + `gecerli_hedefler`):

```
acik ──> kok_neden ──> aksiyon_plani ──> uygulama ──> dogrulama ──> kapandi*
  │          │              │                │            │  │
  │          │              │                │            │  └─> uygulama  (doğrulama başarısız → geri)
  └──────────┴──────────────┴────────────────┴────────────┴─> iptal*
```

- `GECISLER = { acik: {kok_neden, iptal}, kok_neden: {aksiyon_plani, iptal}, aksiyon_plani: {uygulama, iptal}, uygulama: {dogrulama, iptal}, dogrulama: {kapandi, uygulama, iptal}, kapandi: {}, iptal: {} }`
- `ILK_DURUM = "acik"`; `TERMINAL_DURUMLAR = {kapandi, iptal}`.
- Geçiş izni katmanı: **tüm** geçişler `kalite:yaz` (ayrı onay izni yok).

### 3.2 Servis katmanı
**`kalite/service.py`**
- `capa_durum_gecisi(db, uygunsuzluk, *, hedef, kullanici, kok_neden=None, dogrulama_notu=None)`: saf makineyle doğrula (geçersiz hedef → 422, geçersiz geçiş → 409); `kok_neden` durumuna geçişte `kok_neden` set edilebilir; `kapandi`→`kapanis_tarihi`+`dogrulama_notu`; `flush`. Uygunsuzluk `getir_kilitli` (FOR UPDATE) ile çift-geçiş önlenir. Durum değişiminde realtime `kalite.uygunsuzluk` yayını.
- `aksiyon_ekle(db, uygunsuzluk, *, tur, aciklama, sorumlu_id, termin_tarihi)` / `aksiyon_guncelle(db, aksiyon, *, durum, tamamlanma_tarihi)`.
- `kontrol_olustur(...)` — denetim kaydı; oto kod flush sonrası set.
- Oto kod: `kalite_kontrol_kod(id) → KK-{yıl}-{id:06d}`, `uygunsuzluk_kod(id) → UY-{yıl}-{id:06d}` (iş emri/satınalma deseni: flush→id→kod update).
- Uygunsuzluk açılışında outbox `kalite.uygunsuzluk` (transactional) **ve** realtime `kalite.uygunsuzluk`.

**`enerji/service.py`**
- `olcum_yaz(db, *, makine_id, enerji_turu, tuketim, birim, zaman, kullanici) -> EnerjiTuketim`: doğrulama (tür beyaz-liste, `tuketim>0`, makine varsa tenant'ta); append; realtime `enerji.olcum {makine_id}`.

### 3.3 Uçlar `router.py` (hepsi tenant-kapsamlı + RBAC + yazıda audit)

**Kalite kontrol**
- `POST /kalite-kontrolleri` → `kalite:yaz` (makine/iş emri opsiyonel; sonuç/tür beyaz-liste; +audit; realtime `kalite.kontrol`)
- `GET /kalite-kontrolleri` → `kalite:oku` (sayfalama/arama[kod]/sıralama; `makine_id`/`sonuc`/tarih filtresi)
- `GET /kalite-kontrolleri/{id}` → `kalite:oku`

**Uygunsuzluk (CAPA)**
- `POST /uygunsuzluklar` → `kalite:yaz` (başlık + önem; opsiyonel `kaynak_kontrol_id`; durum `acik`; +audit; outbox+realtime `kalite.uygunsuzluk`)
- `GET /uygunsuzluklar` → `kalite:oku` (sayfalama/arama[kod,başlık]/`durum`/`onem` filtresi)
- `GET /uygunsuzluklar/{id}` → `kalite:oku` (aksiyonlar dahil)
- `PATCH /uygunsuzluklar/{id}` → `kalite:yaz` (yalnız aktif durumlarda: başlık/açıklama/önem/sorumlu)
- `PATCH /uygunsuzluklar/{id}/durum` → `kalite:yaz` (gövde `hedef` + ops. `kok_neden`/`dogrulama_notu`; CAPA geçişi)
- `POST /uygunsuzluklar/{id}/aksiyonlar` → `kalite:yaz` (düzeltici/önleyici aksiyon ekle)
- `PATCH /uygunsuzluklar/{id}/aksiyonlar/{aksiyon_id}` → `kalite:yaz` (aksiyon durumu/tamamlanma)

**Enerji**
- `POST /enerji-tuketimleri` → `enerji:yaz` (gövde: `makine_id?, enerji_turu, tuketim, birim, zaman?`; +audit; realtime `enerji.olcum`)
- `GET /enerji-tuketimleri` → `enerji:oku` (`makine_id`/`enerji_turu`/`baslangic`/`bitis` + sayfalama/sıralama)
- `GET /enerji-tuketimleri/trend` → `enerji:oku` (`makine_id`/`enerji_turu`/`baslangic`/`bitis`/`aralik=saat|gun`; CAGG'den nokta dizisi)

## 4. Veri Modeli ve Migration (alembic-fan-out)

Tenant ağacına yeni revizyon. `down_revision` = mevcut tenant head (uygulama anında `alembic heads` ile doğrulanır; bilinen son: `a3d9f1c52e84`). Miktarlar `Numeric(18, 3)`; limitler `Numeric(18, 3)`.

### 4.1 Tablolar
- **`kalite_kontrolleri`** (`KaliteKontrol`, `KimlikMixin`+`ZamanDamgaliMixin`): `kod` (String50, **unique**, index), `makine_id` (FK `makineler.id` **SET NULL**, nullable, index), `is_emri_id` (FK `is_emirleri.id` **SET NULL**, nullable), `kontrol_turu` (String20, default `uretim`), `sonuc` (String20), `olculen_deger`/`alt_limit`/`ust_limit` (Numeric18.3, nullable), `numune_adedi` (Integer, default 0), `uygunsuz_adet` (Integer, default 0), `aciklama` (String1000, default ""), `kontrol_eden_kullanici_id` (FK `kullanici.id` SET NULL, nullable), `zaman` (timestamptz, default now).
- **`uygunsuzluklar`** (`Uygunsuzluk`): `kod` (String50, **unique**, index), `baslik` (String200), `aciklama` (String2000, default ""), `kaynak_kontrol_id` (FK `kalite_kontrolleri.id` **SET NULL**, nullable), `makine_id` (FK `makineler.id` **SET NULL**, nullable), `onem` (String20, default `orta`, index), `durum` (String20, default `acik`, index), `kok_neden` (String2000, default ""), `acan_kullanici_id` (FK SET NULL, nullable), `sorumlu_kullanici_id` (FK SET NULL, nullable), `dogrulama_notu` (String2000, default ""), `kapanis_tarihi` (timestamptz, nullable). `aksiyonlar` relationship (cascade all, delete-orphan).
- **`capa_aksiyonlari`** (`CapaAksiyon`): `uygunsuzluk_id` (FK `uygunsuzluklar.id` **CASCADE**, index), `tur` (String20: `duzeltici|onleyici`), `aciklama` (String1000), `sorumlu_kullanici_id` (FK SET NULL, nullable), `termin_tarihi` (timestamptz, nullable), `durum` (String20, default `planlandi`), `tamamlanma_tarihi` (timestamptz, nullable).
- **`enerji_tuketim`** (`EnerjiTuketim`, **hypertable**): `id` (BigInteger, Identity), `zaman` (timestamptz), **PK `(zaman, id)`**, `makine_id` (FK `makineler.id` **SET NULL**, nullable), `enerji_turu` (String20), `tuketim` (Numeric18.3), `birim` (String20), index `ix_enerji_tuketim_makine_zaman (makine_id, zaman)` + `ix_enerji_tuketim_turu_zaman (enerji_turu, zaman)`.

### 4.2 Migration adım sırası
1. `op.create_table` × 4 (kalite_kontrolleri, uygunsuzluklar, capa_aksiyonlari, enerji_tuketim) + indeksler/FK'ler — **transaction içinde**.
2. `op.execute("SELECT create_hypertable('enerji_tuketim', 'zaman', if_not_exists => TRUE)")` — transaction içinde çalışır (uretim migration'ında kanıtlı).
3. **`with op.get_context().autocommit_block():`** içinde:
   - `CREATE MATERIALIZED VIEW enerji_tuketim_saatlik WITH (timescaledb.continuous) AS SELECT time_bucket('1 hour', zaman) AS kova, makine_id, enerji_turu, sum(tuketim) AS toplam_tuketim, count(*) AS olcum_adedi FROM enerji_tuketim GROUP BY kova, makine_id, enerji_turu;`
   - `SELECT add_continuous_aggregate_policy('enerji_tuketim_saatlik', start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour', schedule_interval => INTERVAL '1 hour');`

**Neden `autocommit_block`:** `tenant/env.py` her şemayı `context.begin_transaction()` içinde çalıştırır; `CREATE MATERIALIZED VIEW … WITH (timescaledb.continuous)` ve policy ekleme **transaction bloğunda çalışamaz**. `autocommit_block` mevcut transaction'ı commit'leyip autocommit'e geçer. `search_path` env'de `SET` (SET LOCAL değil) ile session-düzeyi ayarlandığından autocommit commit'inden sonra korunur → CAGG doğru tenant şemasında oluşur. Async engine + `run_sync` + `autocommit_block` etkileşimi **ilk fan-out testinde doğrulanır** (S10'un en yüksek teknik riski).

### 4.3 downgrade
FK/bağımlılık ters sırası: `with autocommit_block(): op.execute("DROP MATERIALIZED VIEW IF EXISTS enerji_tuketim_saatlik")` → `drop_table('enerji_tuketim')` → `drop_table('capa_aksiyonlari')` → `drop_table('uygunsuzluklar')` → `drop_table('kalite_kontrolleri')` (indeksleriyle).

**Fan-out DoD:** `public` + ≥2 tenant şemasında up/down testli.

### 4.4 Seed (`kimlik/izinler.py`)
- **Katalog:** `enerji:yaz` eklenir (`"enerji:yaz": "Enerji tüketim girişi"`). `kalite:oku/yaz` zaten var.
- **Yeni varsayılan roller** (görev-ayrımı deseni, S9'daki gibi):
  - `VARSAYILAN_ROLLER["kalite"] = {kalite:oku, kalite:yaz}`
  - `VARSAYILAN_ROLLER["enerji"] = {enerji:oku, enerji:yaz}`
- (`admin` tüm kataloğu; `izleyici` `:oku`'ları [`enerji:oku` dahil] otomatik alır.)

## 5. Olaylar

- **Outbox (transactional, S18 webhook):** `kalite.uygunsuzluk` → `{uygunsuzluk_id, kod, baslik, onem, durum}` (uygunsuzluk açılışında, aynı transaction).
- **Gerçek zaman (`core/gercekzaman.yayinla`, canlı UI):**
  - `kalite.kontrol {id}` (kalite kontrol listesi invalidate)
  - `kalite.uygunsuzluk {id, durum}` (uygunsuzluk listesi/detay invalidate)
  - `enerji.olcum {makine_id}` (enerji listesi + trend invalidate)

## 6. Hata Yönetimi

- Geçersiz CAPA durum hedefi → **422**; durum makinesine aykırı geçiş → **409** (`CakismaHatasi`).
- `kalite:yaz` / `enerji:yaz` izni yok → **403**; `kalite:oku` / `enerji:oku` yok → **403**.
- Bilinmeyen kontrol/uygunsuzluk/aksiyon → **404**; doğrulama (tür/sonuç/önem/tüketim/limit) → **422**.
- Terminal (`kapandi`/`iptal`) uygunsuzlukta `PATCH` içerik → **409** (yalnız aktif düzenlenebilir).
- Bilinmeyen `enerji_turu`/negatif `tuketim` → **422**.
- Geçersiz `aralik` (trend) → varsayılana (`saat`) düşer (SQLi-güvenli beyaz-liste, S6 `siralama` deseni).

## 7. Test Stratejisi (DoD + kritik aileler)

**Birim (saf, DB'siz):**
- `kalite/durum`: tüm geçerli/geçersiz geçişler, `dogrulama→uygulama` geri dönüş, terminal'den çıkış yok, `gecerli_hedefler`.
- `kalite/birimler` + `enerji/birimler`: beyaz-liste doğrulama yardımcıları.

**Entegrasyon (TestClient + test DB):**
- **CAPA yaşam döngüsü:** uygunsuzluk aç → `kok_neden` (kök-neden set) → `aksiyon_plani` → aksiyon ekle (düzeltici+önleyici) → `uygulama` → `dogrulama` → `kapandi` (kapanış_tarihi set); geçersiz geçiş → **409**; `dogrulama→uygulama` geri dönüşü çalışır.
- **Kalite kontrol:** oluştur (oto kod `KK-2026-000001`), listele/filtre (`sonuc`/`makine_id`), sonuç/tür beyaz-liste 422.
- **Aksiyon:** ekle + durum güncelle (`planlandi→tamamlandi`); `tur` beyaz-liste.
- **Enerji yaz/oku:** ölçüm yaz, listele/filtre; tür beyaz-liste 422; negatif `tuketim` 422.
- **CAGG trend (kritik):** birden çok ölçüm yaz → `CALL refresh_continuous_aggregate('enerji_tuketim_saatlik', NULL, NULL)` → `/enerji-tuketimleri/trend?aralik=saat` doğru saatlik toplamları döner; `aralik=gun` günlük toplar; real-time aggregation ile refresh **öncesi** son veri de görünür.
- **Tenant izolasyonu (kritik):** alfa kontrol/uygunsuzluk/enerjisine beta token'ı erişemez (404/403).
- **RBAC 403 (kritik):** `kalite:oku` yok → kalite listeleri 403; `enerji:yaz` yok → enerji POST 403; `enerji:oku` yok → trend 403.
- **Audit:** her yazma (`kontrol`/`uygunsuzluk`/`durum`/`aksiyon`/`enerji`) `denetim_izi` üretir.
- **Sözleşme:** `openapi.json` regen + schemathesis kırmızı değil.
- **Migration fan-out (kritik):** `public` + 2 tenant şemasında up/down; **CAGG + hypertable** iki şemada da kurulur/düşer (autocommit_block async doğrulaması).

**Frontend (Vitest + RTL):**
- `kalite/durum` aynası (backend ile birebir, testli); durum/önem/sonuç rozetleri; izin-duyarlı aksiyon görünürlüğü; hook'lar (TanStack Query) mock fetch ile.

## 8. Frontend `frontend/src/modules/{kalite,enerji}/`

Codegen regen (`npm run codegen`) sonrası tiplenmiş API. Bileşenler (S6/S9 deseni: `SunucuTablo`, hook'lar, rozetler):
- **Kalite kontrol:** `KaliteKontrolListesi` (`SunucuTablo` + sonuç rozeti + makine/tür sütunları), `KaliteKontrolFormu` (oluştur; makine/iş emri seçimi opsiyonel).
- **Uygunsuzluk (CAPA):** `UygunsuzlukListesi` (durum + önem rozetli), `UygunsuzlukDetay` (Drawer: künye + kök-neden + **CAPA durum geçişi** [yalnız geçerli hedefler] + düzeltici/önleyici **aksiyon listesi + ekle/tamamla**), `UygunsuzlukFormu` (oluştur/düzenle; opsiyonel kaynak kontrol).
- **Enerji:** `EnerjiTuketimListesi` (`SunucuTablo` + tür/makine/tarih), `EnerjiGirisFormu` (ölçüm girişi), **`EnerjiTrend`** (ECharts çizgi grafik; makine/tür/aralık [saat/gün] filtreleri; `/trend` verisi).
- **Menü (RBAC-gated):** "Kalite" (`kalite:oku`) → kontroller/uygunsuzluklar; "Enerji" (`enerji:oku`) → tüketim/trend. Rotalar + i18n **TR/EN tam**.
- **Canlı:** `olayIsle` → `kalite.kontrol`/`kalite.uygunsuzluk`/`enerji.olcum` olayları ilgili sorguları invalidate eder.

## 9. Bağımlılıklar ve Operasyon

- **Yeni bağımlılık yok** (mevcut stack: FastAPI/SQLAlchemy/Alembic/TimescaleDB/TanStack/AntD/ECharts).
- **ADR-0012:** `docs/adr/0012-kalite-enerji.md` — Tam CAPA durum makinesi + düzeltici/önleyici aksiyonlar; enerji hypertable; **continuous aggregate + `autocommit_block` fan-out deseni** (ADR-0006'da ertelenen işin kapanışı); real-time aggregation.
- **Veri sözlüğü / README / yol-haritası:** `kalite_kontrolleri`/`uygunsuzluklar`/`capa_aksiyonlari`/`enerji_tuketim` (+ `enerji_tuketim_saatlik` CAGG) + S10 ✅.

## 10. Definition of Done (S10)
- [ ] `ruff`+`mypy` temiz; FE `eslint`+`tsc --strict`+`prettier` temiz.
- [ ] Birim + entegrasyon testleri geçer; **CAPA yaşam döngüsü** + **CAGG trend toplulaştırma** + **tenant izolasyonu** + **RBAC 403** testleri kalıcı.
- [ ] API standart zarf (`{success, message, data, meta}`) + doğru HTTP kodu; `openapi.json` + FE codegen güncel.
- [ ] Migration `public` + ≥2 tenant şemasında fan-out + downgrade (**CAGG dahil, autocommit_block**).
- [ ] Yazma uçları audit üretir.
- [ ] ADR-0012 + veri sözlüğü + README/yol-haritası güncel.
- [ ] CI yeşil; Conventional Commit.
- [ ] **Uçtan uca doğrulama:** uygunsuzluk CAPA akışı (`acik→…→kapandi`) UI'da çalışır; enerji trend grafiği gerçek CAGG verisiyle çizilir (gerçek tarayıcı).
