# S18 — Dış Portal + Webhook + API Entegrasyon (Tasarım)

**Tarih:** 2026-07-10 · **Sprint:** Faz 4 / S18 · **ADR:** 0020

## 1. Amaç

FabrikaOS'u dışa açmak — üç yüzeyle:
1. **Webhook altyapısı:** S4'ten beri biriken transactional outbox (`giden_olaylar`)
   olayları artık **imzalı, sürümlü, retry'lı** HTTP teslimatıyla dış sistemlere akar.
2. **API anahtarı erişimi:** 3. taraf ERP/muhasebe (Logo/SAP/e-Fatura) için uzun ömürlü,
   kapsam kısıtlı anahtar tabanlı salt-veri uçları (`/entegrasyon/*`).
3. **Dış self-servis portal:** müşteri/tedarikçi kullanıcıları (`dis-panel` rolü) yalnız
   kendi firmalarının taleplerini görür/açar (`/dis/*`).

**Kabul (yol haritası):** webhook imzası doğrulanabilir + retry korunur; dış portal
yalnızca `dis-panel` kapsamı.

## 2. Kavramlar ve sözlük (turkce-identifier-standardi)

| Kavram | Identifier | Açıklama |
|---|---|---|
| Webhook aboneliği | `WebhookAboneligi` / `webhook_abonelikleri` | Hedef URL + olay türü seçimi + imza gizli anahtarı (tenant şeması) |
| Webhook teslimatı | `WebhookTeslimati` / `webhook_teslimatlari` | Olay×abonelik başına teslimat denemesi günlüğü (durum + yanıt + retry) |
| API anahtarı | `ApiAnahtari` / `api_anahtarlari` | 3. taraf erişim anahtarı (SHA-256 özet, kapsamlı izin listesi) |
| Gizli anahtar | `gizli_anahtar` | Webhook HMAC imza anahtarı (`whs_` önekli) |
| Teslimat / relay | `relay` | Outbox → abonelik fan-out + HTTP gönderim döngüsü |
| Dış portal | `dis` (`/dis/*`) | Firma-kapsamlı self-servis yüzey |

## 3. Webhook altyapısı

### 3.1 Veri modeli (tenant şeması)

- `webhook_abonelikleri`: `ad`, `url` (https zorunlu — dev'de http serbest değil;
  yalnız test ortamı `localhost`'a izin verir), `gizli_anahtar` (`whs_` + 43 char
  urlsafe; imzalama için düz saklanır, API yanıtlarında **maskeli**, yalnız
  oluşturma/yenilemede tam döner), `olay_turleri` JSONB (katalogdan alt küme; boş =
  hepsi), `aktif` bool.
- `webhook_teslimatlari`: `abonelik_id` FK CASCADE, `olay_id` FK (`giden_olaylar`)
  CASCADE, `olay_turu` (denorm — günlük filtre), `govde` JSONB (gönderilen zarf
  anlık görüntüsü), `durum` (`beklemede→basarili | yeniden_denenecek→…→basarisiz`),
  `deneme_sayisi`, `sonraki_deneme_tarihi`, `son_deneme_tarihi`, `yanit_kodu`,
  `yanit_ozeti` (ilk 500 char), `dis_anahtar` UUID (tüketici idempotency).

### 3.2 Olay kataloğu

`OLAY_TURU_KATALOGU` (entegrasyon modülü sabiti — üretici modüllerdeki sabitlerle aynı
string'ler): `is_emri.kapandi`, `ariza.olustu`, `stok.kritik`, `oee.dustu`,
`sozlesme.yaklasiyor`, `anomali.tespit`, `kalite.uygunsuzluk`, `isg.kaza`.

Eksik iki üretici bu sprintte eklenir (§3.6): `ariza.olustu` ve `oee.dustu`.

### 3.3 Zarf (sürümlü payload) + imza

```json
{
  "surum": "v1",
  "olay_turu": "is_emri.kapandi",
  "dis_anahtar": "<giden_olaylar.dis_anahtar UUID>",
  "olusturma_tarihi": "2026-07-10T12:00:00+00:00",
  "veri": { ...giden_olaylar.govde... }
}
```

Başlıklar: `X-FabrikaOS-Signature: t=<unix>,v1=<hex>` ·
`X-FabrikaOS-Olay: <olay_turu>` · `X-FabrikaOS-Teslimat: <teslimat dis_anahtar>`.

İmza = `HMAC-SHA256(gizli_anahtar, f"{t}.{govde_bytes}")` (Stripe deseni). Saf
fonksiyonlar `imza_uret` / `imza_dogrula` (sabit-zaman karşılaştırma +
`tolerans_sn` yeniden-oynatma koruması) — alıcı tarafın doğrulama reçetesi ADR'de.
`surum`/`v1` çifti ileride v2 zarfa yol açar (abonelik başına sürüm alanı YOK —
YAGNI; zarf sürümü global).

### 3.4 Relay (fan-out + teslimat)

`app/modules/entegrasyon/relay.py` — iki aşama, ikisi de idempotent:

1. **Fan-out:** `giden_olaylar.durum='beklemede'` satırları → olay türüne abone
   **aktif** abonelikler için `webhook_teslimatlari` satırı üret → olay
   `gonderildi` işaretlenir (0 abone de tüketim sayılır; outbox durumu "fan-out
   yapıldı" anlamına evrilir, `gonderim_tarihi` dolar).
2. **Teslimat:** `durum IN (beklemede, yeniden_denenecek) AND sonraki_deneme <= now`
   satırları → imzalı POST (httpx, 10 sn timeout). 2xx → `basarili`; aksi →
   `deneme_sayisi++`, backoff `[1dk, 5dk, 30dk, 2sa, 6sa]`; 6. denemede terminal
   `basarisiz`. Yanıt kodu + gövde özeti günlüğe yazılır.

Koşum: `backend/scripts/webhook_relay.py` — public'ten **aktif** tenant'ları döner,
her şemada `search_path` ile iki aşamayı koşar (ingestion worker deseni; ayrı süreç).
`--tek-tur` (test/e2e determinizmi), `--araligi <sn>` (döngü, varsayılan 10),
`--tenant <slug>` (tek kiracı). HTTP istemcisi enjekte edilebilir (testte
`httpx.MockTransport`). Relay hiçbir iş verisi okumaz — yalnız outbox + webhook
tabloları; kiracı-izole.

### 3.5 Yönetim uçları (`/api/v1/webhooklar`)

| Uç | İzin | Not |
|---|---|---|
| `GET /webhooklar` | `entegrasyon:oku` | maskeli `gizli_anahtar` (`whs_…son4`) |
| `POST /webhooklar` | `entegrasyon:yaz` | yanıt **bir kez** tam anahtar içerir |
| `GET/PATCH/DELETE /webhooklar/{id}` | oku/yaz/yaz | PATCH: ad/url/olay_turleri/aktif |
| `POST /webhooklar/{id}/anahtar-yenile` | `entegrasyon:yaz` | yeni anahtar bir kez döner |
| `GET /webhooklar/olay-turleri` | `entegrasyon:oku` | katalog (FE çipleri) |
| `GET /webhooklar/{id}/teslimatlar` | `entegrasyon:oku` | sayfalı günlük + `durum` filtresi |
| `POST /webhooklar/teslimatlar/{id}/yeniden-dene` | `entegrasyon:yaz` | durumu `beklemede`'ye çeker (terminal `basarisiz` dahil) |

Olay türü doğrulaması katalogdan (S16 `modul_hakki_ayarla` deseni: katalog dışı 422).

### 3.6 Yeni olay üreticileri

- **`ariza.olustu`:** makine durumu **arızaya geçtiğinde** (kenar-tetikli:
  `PATCH /makineler/{id}/durum` hedef `ariza` ∧ önceki ≠ `ariza`) durum değişikliğiyle
  aynı transaction'da outbox olayı yazılır (makine_id/kod/ad + onceki_durum).
  *(Uygulama notu: ayrı bir "arıza kaydı POST" ucu yok — arıza akışı durum
  makinesiyle yaşıyor; olay doğal kaynağına bağlandı.)*
- **`oee.dustu`:** `POST /oee/dusuk-tara` (izin `uretim:yaz`) — kenar-tetikli tarama
  (S12 `yaklasan-tara` deseni): her aktif makinenin **bugünkü** OEE'si `esik`
  (varsayılan 0.60) altındaysa olay yazar; aynı makine+gün için ikinci olay
  üretilmez (dedup outbox sorgusuyla: `olay_turu + govde->makine_id + govde->tarih`).

## 4. Entitlement (S16 tüketimi)

- `MODUL_KATALOGU`'na iki modül: `entegrasyon` (webhook + API anahtarları),
  `dis-portal` (müşteri self-servis). İkisi de yalnız `deneme`/`kurumsal`
  planlarında (satış üst-segment eklentisi); `temel`/`profesyonel` değişmez.
  Plan senkronu provizyon upsert'iyle (yeni public migration GEREKMEZ — ADR-0018).
- **`webhook-onizleme` bayrağı tüketilir** (S16 mekanizması): webhook yönetim uçları
  `entegrasyon` modülü **VEYA** bayrak açıksa erişilir (`webhook_erisimi_gerekli`
  dependency). Platform admin (S17 PUT ozellik-bayraklari) böylece modülü satın
  almamış bir tenant'a webhook ön izlemesi verebilir.
- API anahtarı yönetimi + `/entegrasyon/*` + `/dis/*` sıkı modül kapısı
  (`modul_gerekli("entegrasyon")` / `modul_gerekli("dis-portal")`) — bayrak geçmez.

## 5. API anahtarı erişimi

### 5.1 Model + yaşam döngüsü

`api_anahtarlari`: `ad`, `onek` (görüntü kimliği, ilk 12 char), `anahtar_ozet`
(SHA-256 hex — **düz anahtar asla saklanmaz**), `izinler` JSONB (yalnız
`ENTEGRASYON_IZIN_KAPSAMLARI = {uretim:oku, stok:oku, satinalma:oku}` alt kümesi),
`aktif`, `gecerlilik_tarihi` (null = süresiz), `son_kullanim_tarihi`,
`olusturan_kullanici_id`.

Anahtar biçimi: `fos_` + `secrets.token_urlsafe(32)`. Oluşturmada **bir kez** tam
döner; listede yalnız `onek`. İptal = DELETE (kalıcı) veya PATCH `aktif=false`.

### 5.2 Kimlik doğrulama

Başlık `X-API-Anahtar` (JWT `Authorization` ile karışmaz). Akış: `tenant_cozumle`
(X-Tenant/subdomain — anahtar tenant şemasında yaşadığı için arama zaten izole) →
SHA-256 özet eşleşmesi → `aktif` + geçerlilik kontrolü → `son_kullanim_tarihi`
güncelle. Başarısız her dal **401** (anahtar var/yok ayrımı sızdırılmaz).
`api_izin_gerekli("stok:oku")` anahtarın `izinler` listesini kontrol eder (403).

### 5.3 Dış veri uçları (`/api/v1/entegrasyon/*`)

Salt-okunur, ERP/muhasebe senkron ihtiyaçları (hepsi `modul_gerekli("entegrasyon")`):

| Uç | Kapsam | İçerik |
|---|---|---|
| `GET /entegrasyon/stok-bakiyeleri` | `stok:oku` | malzeme kod/ad/birim/bakiye/kritik_esik (sayfalı) |
| `GET /entegrasyon/satinalma-talepleri` | `satinalma:oku` | `?durum=onaylandi` varsayılan — ERP'de PO'ya dönecek talepler + kalemler |
| `GET /entegrasyon/uretim-ozeti` | `uretim:oku` | `?gun=YYYY-MM-DD` makine başına üretilen/fire + OEE (mevcut `oee_hesapla`) |

İç RBAC'e dokunulmaz: bu yüzeyin kendi dependency zinciri var; JWT uçları
etkilenmez (blast radius = 0).

## 6. Dış portal (`/api/v1/dis/*`)

- `kullanici.firma_id` (nullable FK `firmalar.id` SET NULL): dış kullanıcıyı CRM
  firmasına bağlar. `POST/PATCH /kullanicilar` DTO'larına opsiyonel `firma_id`
  eklenir (admin dış kullanıcıyı böyle açar: rol `dis-panel` + firma).
- Yeni izin `dis:erisim`; rol `dis-panel` = yalnız `{dis:erisim}` (skill: iç modül
  izinleriyle karışmaz — iç uçların tamamı başka izin istediği için dis-panel
  kullanıcısı yapısal olarak dışarıda kalır).
- `dis_firma_gerekli` dependency: `izin_gerekli("dis:erisim")` + `firma_id` dolu
  (boşsa 403 "firma bağlantısı yok" — admin her izne sahip ama firmasız olduğundan
  /dis'e giremez; **filtre dependency'de zorlanır**, controller'a bırakılmaz).
- Uçlar (`modul_gerekli("dis-portal")`):
  - `GET /dis/talepler` — yalnız kendi firması (sayfalı, `durum` filtresi).
  - `POST /dis/talepler` — başlık/açıklama/tür/öncelik; `firma_id` **sunucuda**
    kullanıcının firmasından atanır, `talep_eden_kullanici_id` oturumdan; mevcut
    talep servisi (TL- kod + durum makinesi + realtime) yeniden kullanılır.
  - `GET /dis/talepler/{id}` — başka firmanın talebi **404** (görünmez).
  - `GET /dis/durum` — firma adı + talep durum kırılımı + son 5 talep.

## 7. Frontend

### 7.1 `/webhooklar` (Yönetim, slate — uiplani §11.1)

Tek ekran, üç sekme: **Abonelikler** (URL, olay türü çipleri, maskeli anahtar +
kopyala, aktif switch; oluşturma modalı → anahtar bir-kez göster + kopyala) ·
**Teslimat Günlüğü** (durum pimi başarılı/yeniden deneniyor/başarısız + yanıt kodu +
payload çekmecesi + yeniden dene) · **API Anahtarları** (onek, kapsam çipleri,
geçerlilik; oluşturmada bir-kez göster). Menü: `entegrasyon` modülü (fail-open) +
`entegrasyon:oku`.

### 7.2 Dış portal `/dis` (kabuksuz hafif kabuk)

Aynı SPA, ayrı hafif kabuk (S15 kiosk deseni): sidebar yok; üst bar = tenant adı
(markalama alanı) + sekmeler **Taleplerim · Yeni Talep** + çıkış. Talep detayı
çekmecede **durum zaman çizelgesi** (müşteri-dili durum adları: `acik`→"Alındı",
`isleniyor`→"İşleme alındı", `cozuldu`→"Çözüldü", `kapandi`→"Kapatıldı",
`iptal`→"İptal edildi"). Giriş: normal `/giris`; `dis:erisim` olan ve iç okuma izni
olmayan kullanıcı girişte `/dis`'e yönlenir; `/dis` rotası `KorunanRota
izin="dis:erisim"`.

## 8. Test stratejisi

- **Saf:** imza üret/doğrula (tolerans, yanlış anahtar, oynanmış gövde), backoff
  dizisi, zarf üretimi, maskeleme.
- **Migration:** head'de 3 tablo + `kullanici.firma_id` var; down→yok; up→geri.
- **Webhook uçları:** RBAC 403, maskeleme, bir-kez anahtar, katalog dışı olay 422,
  tenant izolasyonu (A'nın aboneliği B'de görünmez).
- **Relay:** fan-out (2 abone → 2 teslimat; eşleşmeyen tür → 0; olay `gonderildi`),
  teslimat (MockTransport 200 → `basarili` + imza başlığı alıcıda doğrulanır;
  500 → backoff `yeniden_denenecek`; 6. deneme → `basarisiz`; yeniden-dene ucu
  sıfırlar), izolasyon (tenant A olayı B aboneliğine gitmez).
- **API anahtarı:** doğru anahtar 200, yanlış/pasif/süresi dolmuş 401, kapsam dışı
  403, özet-saklama (DB'de düz anahtar yok), izolasyon.
- **Entitlement:** `temel` planda webhook 403 `MODUL_KAPALI`; `webhook-onizleme`
  bayrağı override ile açılır; `/dis` `dis-portal` modülü kapalıysa 403.
- **Dış portal:** firma A kullanıcısı B'nin talebini göremez (liste 0 + detay 404),
  firmasız 403, dis-panel iç uca (`/makineler`) 403, portal talebi iç listede görünür.
- **FE:** vitest — webhook ekranı sekmeleri/bir-kez modal, portal kabuğu + zaman
  çizelgesi, menü görünürlüğü.

## 9. Riskler / bilinçli kararlar

- **Gizli anahtar düz saklanır** (imzalama gerektirir) — DB zaten kiracı-izole;
  API'de maskeli. At-rest şifreleme S23 (kurumsal güvenlik) adayı.
- **Relay ayrı süreç** (ingestion deseni): uygulama restart'ından bağımsız, yatay
  ölçeklenebilir; dev/e2e'de `--tek-tur` determinizm sağlar. Uygulama-içi arka plan
  görevi bilinçli reddedildi (uvicorn çoklu worker'da çift teslimat riski).
- **`dis-panel` kullanıcıları koltuk limitine dahil** (S16 sayacı değişmez) —
  muafiyet ticari karar; ADR'de not, gerekirse S23'te.
- **Outbox `durum` anlamı evrildi:** `gonderildi` = "fan-out yapıldı" (teslimat
  durumu artık `webhook_teslimatlari`'nda satır başına). Eski `basarisiz` değeri
  outbox'ta kullanılmaz oldu; veri sözlüğüne not düşülür.
