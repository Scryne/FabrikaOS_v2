# ADR-0020: Dış Portal + Webhook + API Entegrasyon — dışa açılan üç yüzey

Durum: Kabul
Tarih: 2026-07-10

## Bağlam
Faz 4 / S18: ürünü dışa açmak. S4'ten beri transactional outbox (`giden_olaylar`)
"teslimat S18'de" notuyla olay biriktiriyordu; S16 `webhook-onizleme` bayrağını
"tüketimi S18'de" diye katalogladı; tenant-rbac-conventions skill'i dış paneli
(`dis-panel`, `/api/v1/dis/*`, firma-kapsamı dependency'de) baştan sözleşmeye
bağlamıştı. Kabul: webhook imzası doğrulanabilir + retry korunur; dış portal
yalnızca `dis-panel` kapsamı.

## Karar

### Webhook altyapısı
- **Fan-out modeli:** outbox satırı (`beklemede`) → olay türüne abone **aktif**
  aboneliklere `webhook_teslimatlari` satırları açılır → olay `gonderildi` işaretlenir.
  `gonderildi`nin anlamı S18'de **"fan-out yapıldı"ya evrildi** — teslimat durumu
  artık abonelik×olay başına teslimat satırında yaşar (0 abone de tüketimdir).
- **İmza (Stripe deseni):** `X-FabrikaOS-Signature: t=<unix>,v1=<hex>`;
  `HMAC-SHA256(gizli_anahtar, f"{t}." + ham_govde)`. `t` imzaya dahil →
  alıcı `tolerans_sn` (varsayılan 300) ile yeniden-oynatmayı reddeder; doğrulama
  sabit-zamanlıdır. Gövde **sürümlü zarftır** (`surum: "v1"`, olay_turu,
  dis_anahtar = tüketici idempotency anahtarı, olusturma_tarihi, veri). Ek
  başlıklar: `X-FabrikaOS-Olay`, `X-FabrikaOS-Teslimat`.
- **Gizli anahtar (`whs_`+43) düz saklanır** — her teslimatta imzalama gerektirir;
  API'de her zaman maskeli, tam değer yalnız oluşturma/anahtar-yenile yanıtında
  (bir kez). At-rest şifreleme S23 adayı.
- **Retry:** backoff `1dk→5dk→30dk→2sa→6sa`, toplam 6 deneme → terminal `basarisiz`.
  Panelden **yeniden-dene** terminal dahil bir deneme daha kuyruğa alır (son-şans
  semantiği; deneme sayacı korunur). 2xx = başarı; yanıt kodu + ilk 500 karakter
  günlüğe yazılır.
- **Relay ayrı süreçtir** (`scripts/webhook_relay.py`, ingestion worker deseni):
  aktif tenant'larda döngü, şema başına `search_path` + kendi transaction'ı.
  Uygulama-içi arka plan görevi bilinçli reddedildi (çoklu uvicorn worker'da çift
  teslimat riski; ayrı süreç yatay ölçeklenir). `--tek-tur` e2e determinizmi sağlar.
  Relay iş verisi okumaz — yalnız outbox + webhook tabloları (kiracı-izole).
- **Olay kataloğu 8 tür:** is_emri.kapandi, ariza.olustu, stok.kritik, oee.dustu,
  sozlesme.yaklasiyor, anomali.tespit, kalite.uygunsuzluk, isg.kaza. Eksik iki
  üretici bu sprintte eklendi: `ariza.olustu` makine durumunun **arızaya geçişinde**
  kenar-tetikli (ayrı arıza POST ucu yok — olay doğal kaynağına bağlandı);
  `oee.dustu` `POST /oee/dusuk-tara` taramasıyla (eşik = `makine.oee_hedefi`,
  yoksa parametre; makine+gün dedup outbox sorgusuyla — S12 `yaklasan-tara`
  deseninin durumsuz eşdeğeri).

### Entitlement (S16 tüketimi)
- İki yeni modül: **`entegrasyon`** (webhook + API anahtarları) ve **`dis-portal`**
  (müşteri self-servis) — yalnız `deneme`/`kurumsal` planlarında (üst-segment
  eklenti). Plan senkronu provizyon upsert'iyle; **public migration gerekmedi**.
- **`webhook-onizleme` bayrağı tüketildi:** webhook uçları
  `modul_veya_ozellik_gerekli("entegrasyon", "webhook-onizleme")` — modülü satın
  almamış tenant'a platform admin bayrakla ön izleme verebilir (S17 PUT
  ozellik-bayraklari ile; bir sonraki istekte etkili). API anahtarı yönetimi +
  `/entegrasyon/*` + `/dis/*` sıkı modül kapısıdır (bayrak geçmez).
- Yeni izinler `entegrasyon:oku/yaz` + `dis:erisim`; roller `entegrasyon` ve
  `dis-panel` (= yalnız `{dis:erisim}`). Operasyon notu (S16 dersi): canlı
  tenant'larda idempotent provizyon yeniden koşulmalı ki yeni izin/rol/plan insin.

### API anahtarı (3. taraf ERP/muhasebe)
- `api_anahtarlari`: **düz anahtar asla saklanmaz** — SHA-256 özetle aranır/doğrulanır;
  `onek` (ilk 12 karakter) görüntü kimliğidir; tam değer (`fos_`+43) yalnız oluşturma
  yanıtında. Kapsam = `izinler` JSONB, yalnız beyaz-listeden
  (`uretim:oku`/`stok:oku`/`satinalma:oku` — en az ayrıcalık); katalog dışı 422.
- **Kimlik `X-API-Anahtar` başlığıdır** (JWT `Authorization` ile karışmaz);
  tenant `X-Tenant`/subdomain ile çözülür — anahtar tenant şemasında yaşadığından
  arama yapısal olarak izoledir. Eksik/bilinmeyen/pasif/süresi-dolmuş ayrımı
  sızdırılmaz: hepsi 401; kapsam yetersizse 403. `son_kullanim_tarihi` her istekte
  güncellenir.
- **Dış veri yüzeyi `/api/v1/entegrasyon/*` ayrı ve salt-okunurdur:** stok-bakiyeleri,
  satinalma-talepleri (`?durum=onaylandi` → ERP'de PO'ya dönecekler), uretim-ozeti
  (gün + makine başına adet/fire/OEE). İç RBAC zincirine dokunulmadı (blast radius 0);
  anahtarın tüm API'ye erişimi bilinçli reddedildi — genişleme ihtiyacı doğarsa ayrı
  karar olur.

### Dış portal
- `kullanici.firma_id` (nullable FK `firmalar`): dış kullanıcıyı CRM firmasına bağlar;
  admin `POST /kullanicilar`'da rol `dis-panel` + `firma_id` ile açar.
- **Firma süzgeci dependency'de zorlanır** (`dis_firma_kullanici` = `dis:erisim` +
  firma bağlantısı; skill sözleşmesi): başka firmanın talebi listede yoktur, ID ile
  404 (görünmez). Firmasız kullanıcı — admin dahil (tüm izinlere sahip ama firmasız) —
  403. `dis-panel` rolü tek izin taşıdığından dış kullanıcı iç uçlarda yapısal 403.
- Portal talebi iç `talep` tablosuna yazar (tek doğruluk kaynağı): TL- kod + durum
  makinesi + `talep.olusturuldu` gerçek-zaman sinyali aynen; iç ekipte anında görünür.
  Dış DTO iç alanları (atama, firma_id) sızdırmaz.
- **FE `/dis` kabuksuz hafif kabuk** (kiosk deseni): sidebar yok; marka + firma adı
  (markalama alanı) + Taleplerim/Yeni Talep sekmeleri; durum adları müşteri dilinde
  (`acik`→"Alındı"…), detayda durum zaman çizelgesi. Girişte **yalnız** `dis:erisim`
  taşıyan kullanıcı `/dis`e yönlenir (`sadeceDisKullanici` saf yardımcı).

### FE /webhooklar (Yönetim)
Üç sekme: Abonelikler (maskeli anahtar, olay çipleri, aktif switch, anahtar-yenile) ·
Teslimat Günlüğü (durum pimi + payload çekmecesi + yeniden dene) · API Anahtarları.
"Bir kez göster" modalı kopyala butonuyla. Rota kapısı `EntegrasyonKapisi` = modül
VEYA bayrak (backend dependency'sinin UI aynası; fail-open). Bilinen kozmetik sınır:
yalnız-bayraklı tenant'ta menü öğesi gizlidir (modül süzgeci), doğrudan URL çalışır.

## Sonuçlar
- Faz 4 kapısı geçildi: entitlement (S16) + platform admin (S17) + dış portal/webhook/
  API anahtarı (S18) — ürün modül modül satılabilir ve dışa entegre edilebilir durumda.
- Outbox artık uçtan uca canlı: S4'te yazılan olaylar imzalı HTTP ile dışarı akıyor;
  yeni modüller `olay_yayinla` + katalog satırı eklemekle webhook'lanır.
- `dis-panel` kullanıcıları koltuk limitine DAHİL (S16 sayacı değişmedi) — muafiyet
  ticari karar; gerekirse S23'te ayrı sayaç.
- Relay operasyonel bir süreçtir: dev/e2e'de elle `--tek-tur`, üretimde servis olarak
  koşar (S19 gözlemlenebilirlik sprintinde metrik/alarm bağlanır).
- Alıcı doğrulama reçetesi (imza) bu ADR + spec'te belgeli; e-Fatura/Logo/SAP tarafı
  anahtar + webhook kombinasyonuyla çift yönlü entegre olabilir.
