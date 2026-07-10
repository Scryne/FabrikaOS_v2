# S17 — Platform Admin Paneli (Tasarım)

**Tarih:** 2026-07-10 · **Sprint:** Faz 4 / S17 · **ADR:** 0019

## 1. Amaç

Control-plane'i API + panel ile yönetilebilir kılmak: platform operatörü tenant'ları
**dakikalar içinde provizyonlar**, planı/entitlement'ı değiştirir (S16'nın ertelediği
yazma API'si), askıya alır (erişim ANINDA kesilir), **KVKK ihracı** alır ve siler.
Tümü tenant düzleminden yapısal olarak ayrık bir kimlikle yapılır.

## 2. Kavramlar ve sözlük (turkce-identifier-standardi)

| Kavram | Identifier | Açıklama |
|---|---|---|
| Platform yöneticisi | `PlatformYonetici` / `platform_yonetici` | Control-plane operatör hesabı (public şema; tenant RBAC'inden ayrık) |
| Tenant ihracı | `TenantIhrac` / `tenant_ihraclari` | KVKK dışa aktarma işi (durum makinesi + ZIP artefaktı) |
| Platform denetim izi | `PlatformDenetimIzi` / `platform_denetim_izi` | Control-plane yazma işlemlerinin kim-ne-ne zaman kaydı |

`platform_yonetici` tablo adı alembic-fan-out skill'indeki control-plane referansıyla
birebir; `tenant_ihraclari` S16'nın `modul_haklari` çoğul kalıbını izler.

## 3. Kimlik düzlemi (EN KRİTİK karar)

- Platform yöneticisi **`public.platform_yonetici`** tablosunda yaşar — hiçbir tenant
  şemasına bağlı değildir. Tenant `Kullanici`/RBAC'i ile kesişmez (`platform-admin`
  tenant izin kataloğunda YOKTUR; skill'de belgelidir).
- Aynı JWT altyapısı, **ayrı token tipleri**: `platform_access` / `platform_refresh`
  (`jwt.coz(token, beklenen_tip)` tip kontrolü mevcut). Tenant token'ı platform
  ucunda, platform token'ı tenant ucunda **yapısal olarak** geçersizdir (tip uyuşmaz
  → 401). `tenant_slug` claim'i platform token'larında `"platform"` sabitidir (inert).
- Refresh rotasyonu + Redis iptal listesi (`token_deposu`) aynen yeniden kullanılır;
  giriş ucu `giris:platform:<ip>` anahtarıyla rate-limit'lidir.
- Platform uçları `tenant_cozumle`'den GEÇMEZ (skill'deki belgeli istisna):
  `X-Tenant`/subdomain okunmaz; sorgular `PublicBase` (schema="public") üzerinden.
- İlk yönetici CLI ile açılır: `backend/scripts/platform_yonetici_olustur.py`
  (argon2id, eposta üzerinden idempotent upsert).

## 4. Veri modeli (public / control-plane; tek migration)

- `platform_yonetici`: `eposta` uq, `parola_ozet`, `ad_soyad`, `aktif`,
  `son_giris_tarihi` (Kullanici ile aynı kalıp, rolsüz — tüm platform yöneticileri eşit).
- `tenant_ihraclari`: `tenant_id` FK CASCADE, `slug` (denorm — artefakt anahtarı),
  `durum` (`kuyrukta→hazirlaniyor→hazir|basarisiz`), `nesne_anahtari`, `boyut`,
  `tablo_sayisi`, `hata`, `olusturan_eposta`.
- `platform_denetim_izi`: `yonetici_id`, `yonetici_eposta`, `eylem`, `kaynak`,
  `kaynak_id`, `request_id`, `ip_adresi`, `detay` JSONB (tenant `denetim_izi` aynası).

Tenant ağacına dokunulmaz → **fan-out yok**; yalnız public up/down.

## 5. Uçlar (`/api/v1/platform/*`)

Kimlik: `POST /platform/kimlik/token` (OAuth2 form, rate-limit) ·
`POST /platform/kimlik/yenile` (rotasyon) · `POST /platform/kimlik/cikis` ·
`GET /platform/kimlik/ben`. Diğer tüm uçlar `mevcut_platform_yonetici` korumalı.

Tenant yönetimi:
- `GET /platform/tenantlar` — sayfalı + `arama` (slug/ad ILIKE); satırda plan kodu,
  abonelik durumu, aktiflik, **koltuk kullanımı** (şema varsa `to_regclass` korumalı sayım).
- `POST /platform/tenantlar` — gövde: slug/ad/plan_kodu/admin_eposta/admin_parola;
  `tenant_provizyonla`'yı senkron çağırır (idempotent, saniyeler; 202'ye yükseltme
  yolu ADR'de). Var olan slug → 409.
- `GET /platform/tenantlar/{id}` — künye + abonelik + plan + koltuk + etkin
  modül/özellik matrisi (kaynak: plan|hak).
- `PATCH /platform/tenantlar/{id}` — `ad` ve/veya `plan_kodu` (katalog dışı → 422;
  geçerli abonelik yoksa 409). Plan değişimi ANINDA etkilidir (S16 önbelleksiz).
- `POST /platform/tenantlar/{id}/askiya-al` / `/aktiflestir` — `tenant.aktif` bayrağı;
  `tenant_cozumle` aktif olmayanı 404'lediği için erişim **bir sonraki istekte** kesilir.
- `DELETE /platform/tenantlar/{id}` — gövdede `onay` alanı **slug ile birebir eşleşmek
  zorunda** (GitHub deseni; değilse 422). `DROP SCHEMA tenant_<slug> CASCADE` + public
  satırı (FK CASCADE: abonelik/haklar/bayraklar/ihraçlar) silinir. Geri dönüşsüz.

Entitlement yazma (S16 devri):
- `PUT /platform/tenantlar/{id}/modul-haklari/{modul_kodu}` — gövde `{acik: bool|null}`
  (`null` = override kaldır, plana dön). `entitlement_service` yeniden kullanılır;
  katalog dışı kod → 422. Etki bir sonraki tenant isteğinde (önbellek yok).
- `PUT /platform/tenantlar/{id}/ozellik-bayraklari/{kod}` — aynı sözleşme.

Katalog/izleme:
- `GET /platform/abonelikler` — abonelik × tenant × plan birleşik listesi (sayfalı).
- `GET /platform/planlar` — plan kataloğu (provizyon sihirbazı için).
- `GET /platform/saglik` — db/redis/nesne deposu sonda durumları + tenant sayıları
  (toplam/aktif/askıda) + sürüm; her sonda try/except (kısmi arıza panoyu düşürmez).

KVKK ihracı (S14 rapor deseninin yeniden kullanımı):
- `POST /platform/tenantlar/{id}/ihrac` → `tenant_ihraclari` kaydı (`kuyrukta`) + 202;
  süreç-içi async görev kendi oturumunda: public kayıtlar (tenant/abonelik/haklar/
  bayraklar) + **tenant şemasındaki TÜM tablolar** (`information_schema`'dan keşif —
  gelecek modüller otomatik kapsanır = "eksiksiz" garantisi şemaya değil keşfe bağlı)
  tablo-başına JSON → tek ZIP (+`manifest.json`) → `NesneDepo`'ya
  **`platform/ihrac/<slug>/<id>/<dosya>.zip`** anahtarı (tenant `tenant_<slug>/...`
  önekinin DIŞINDA: artefakt control-plane'e aittir) → `hazir`.
- `GET /platform/ihraclar?tenant_id=` — durum listesi (yoklamayla izlenir).
- `GET /platform/ihraclar/{id}/indir` — ZIP baytları; `hazir` değilse 409.
- Testler `oturum_fabrikasi_ayarla` + `es_zamanli_ayarla(True)` enjeksiyonlarını
  (S13/S14 imzaları) aynen kullanır.

Tüm yazma uçları `platform_denetim_yaz` ile `platform_denetim_izi`'ne işlenir.

## 6. Frontend (aynı SPA içinde ayrı düzlem; uiplani §11.1)

- Rotalar `/platform/*` (ayrı subdomain'e taşıma Faz 5 operasyon işi; kod düzeyinde
  düzlem ayrımı bugün kurulur — ADR'de). Tenant kabuğu/menüsünden tamamen ayrık.
- **Ayrı kimlik düzlemi:** `platformAuthStore` (access bellekte, refresh
  `localStorage["fabrikaos_platform_refresh"]`) + `platformIstemci` (X-Tenant başlığı
  YOK, 401→`/platform/kimlik/yenile` single-flight→tek tekrar). Tenant istemcisine
  dokunulmaz.
- **Kimlik rengi:** "platform" hattı turuncu `#f97316` (tenant UI'ında kullanılmıyor) +
  kabukta kalıcı **"PLATFORM" filigran çipi** — yanlış düzlemde işlem riskine karşı
  hangi düzlemde olunduğu her an belli.
- Ekranlar: `TenantListesi` (durum/plan/koltuk kullanımı) · `TenantDetay` (künye,
  koltuk progress, entitlement matrisi switch'leri, özellik bayrakları, **tehlikeli
  aksiyonlar**: askıya al / ihraç / sil) · `ProvizyonSihirbazi` (Steps: slug → plan →
  admin → özet) · `SaglikPano` (LED dili) · `AbonelikListesi`.
- **Tehlikeli aksiyon deseni:** askıya alma/silme → slug'ı **yazarak onaylama** modalı;
  ihraç 202 sonrası listede durum yoklaması + hazır olunca indirme.
- i18n TR/EN (`platform.*` anahtarları); tüm metin `t()`.

## 7. Kabul kriterleri (yol haritası S17)

1. Panelden yeni tenant provizyonlanır ve admin'i dakikalar içinde giriş yapar
   (API testi: provizyon → yeni tenant'a `kimlik/token` 200).
2. Askıya alma erişimi keser: askıdaki tenant'ın tüm uçları (giriş dahil) 404;
   aktifleştirme geri açar.
3. İhraç ZIP'i tenant verisini eksiksiz içerir (test: bilinen kullanıcı e-postası
   `kullanici.json`'da; tablo sayısı manifest'te; bayt düzeyi indirme eşleşmesi).
4. Entitlement yazma ANINDA etkili: PUT modül kapat → tenant'ın bir sonraki isteği
   403 `MODUL_KAPALI`; `null` → plana döner.
5. Düzlem ayrımı: tenant admin token'ı platform uçlarında 401; platform token'ı
   tenant uçlarında 401; kimliksiz 401.
6. Silme yalnız `onay == slug` ile; şema düşer, public kayıtlar kaskatlı silinir.
7. Migration public ağacında up/down; platform yazmaları `platform_denetim_izi`'nde.
