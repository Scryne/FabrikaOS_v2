# ADR-0022 — Kurumsal Güvenlik & Uyum: 2FA, SSO (OIDC), Oturum Yönetimi, Denetim Görünürlüğü, KVKK (S23)

- **Durum:** Kabul edildi (S23, Faz 6)
- **Tarih:** 2026-07-30
- **İlgili:** ADR-0005 (OAuth2/JWT/RBAC), ADR-0003 (şema-başına-tenant), ADR-0016 (async
  rapor deseni), ADR-0019 (platform control-plane + KVKK tenant ihracı)

## Bağlam

GA öncesi kimlik yüzeyi tek faktörlüydü: parola + rotasyonlu refresh. Kurumsal müşteri
sözleşmelerinde standart olan **2FA**, **kurumsal SSO**, **parola politikası**, **oturum/cihaz
görünürlüğü** ve **IP kısıtı** yoktu. `core/audit.py` kim-ne-ne zaman üretiyordu ama
görüntülenemiyordu (denetlenebilirlik iddiası kanıtlanamıyordu). KVKK tarafında S17 ile
**tenant bazlı** ihraç vardı; **kişi bazlı** ihraç, anonimleştirme ve rıza kaydı yoktu.

Bu sprint güvenlik/uyumu **çekirdek hak** olarak konumlar: `modul_gerekli` entitlement
kapısı **uygulanmaz** (satılabilir yetenek değil), yalnız RBAC izinleriyle korunur.

## Karar

### 1. TOTP 2FA (kullanıcı düzeyinde)

`kullanici.totp_sirri` + `iki_asama_aktif`; `kurtarma_kodlari` (yalnız SHA-256 özeti,
bir kez kullanılır). Kurulum üç adım: sır üret → authenticator kodu doğrula → kurtarma
kodlarını **bir kez** göster. `iki_asama_aktif` yalnız **doğrulanmış** kurulumla `True`
olur (yarım kurulum girişi kilitlemez).

Giriş akışı yapısal olarak ayrılır: parola doğruysa ve 2FA açıksa tam token çifti YERİNE
5 dk ömürlü **`tip="2fa"`** token döner. Ayrı `tip` değeri, bu token'ın access olarak
kullanılmasını yapısal olarak imkânsız kılar (ADR-0019'daki platform düzlemi ayrımının
aynısı). İkinci adım tek kullanımlıktır (`jti` Redis iptal listesine yazılır).

### 2. Tenant güvenlik ayarları (control-plane)

`public.tenant.guvenlik_ayarlari` JSONB: `parola` politikası, `iki_asama_zorunlu`,
`ip_izin_listesi`, `oidc`. Neden JSONB ve neden `public`:

- Giriş, tenant şeması açılmadan **önce** gerçekleşir → ayarların control-plane'de olması şart.
- Kural kümesi ürün ömrü boyunca genişler; her kural için kolon eklemek migration borcu üretir.

`iki_asama_zorunlu` açıkken 2FA'sız kullanıcı `kurulum=true` işaretli geçici token alır ve
yalnız kurulum uçlarına erişebilir (yarım oturumla veri okunamaz).

**IP izin listesi** `tenant_cozumle` içinde her istekte uygulanır; satır bazında fail-open
(bozuk CIDR satırı atlanır, liste bütünüyle geçersiz sayılmaz) — yanlış bir girdi tenant'ı
kilitlemesin. Liste boşsa kısıt yoktur.

### 3. Kurumsal SSO — OIDC Authorization Code + PKCE

Saf çekirdek (`core/security/oidc.py`) / ağ kenarı ayrımı: URL kurma, PKCE, claim eşleme,
alan adı ve grup→rol kuralları **saf fonksiyonlardır**; ağ erişimi `OidcAgIstemcisi`
protokolünün arkasındadır (`NesneDepo`/`BellekNesneDepo` deseni). Testler gerçek RSA anahtarı
üreten, gerçek JWKS yayınlayan ve id_token'ı RS256 imzalayan `SahteIdp` enjekte eder.

Kritik kararlar:

- **Claim adları sabit değil.** Azure AD `preferred_username`, Keycloak `realm_access.roles`
  verir; hangi claim'in neyi taşıdığı tenant başına `claim_eslemesi` ile ayarlanır. İç içe
  yol nokta ile yazılır (`realm_access.roles`).
- **`redirect_uri` istemciden ALINMAZ**, tenant yapılandırmasından gelir (açık yönlendirme
  koruması).
- **State tek kullanımlıktır** (Redis'te tutulur, tamamlamada silinir) ve tenant'ı taşır:
  A tenant'ında başlatılan akış B'de tamamlanamaz (403).
- **JWKS önbelleği + rotasyon:** issuer başına TTL'li önbellek; bilinmeyen `kid` görülürse
  önbellek **bir kez** zorla tazelenir → IdP anahtar döndürdüğünde kesinti olmaz.
- **Saat kayması** `saat_kaymasi_sn` (vars. 120) ile `exp`/`iat` doğrulamasına tolerans verir.
- **JIT provizyon** koltuk limitini parola akışıyla **aynı** `koltuk_kontrol` üzerinden zorlar
  (S16 limiti SSO'dan delinemez). JIT hesaba kullanılamaz parola özeti yazılır: hesap yalnız
  IdP üzerinden erişilebilir.
- **Grup→rol senkronu** yalnız `grup_rol_eslemesi` yapılandırılmışsa çalışır ve
  `varsayilan_roller`e **geri düşmez** — düşseydi, eşleşmeyen grup gören mevcut kullanıcı her
  girişte varsayılana düşürülür, sessizce yetki kaybederdi. Eşleme hiçbir geçerli rol
  vermezse mevcut roller korunur.
- **2FA kesişimi:** kullanıcı kendi TOTP'sini açtıysa SSO sonrası da ikinci adım istenir.
  Tenant'ın `iki_asama_zorunlu` ayarı SSO girişinde **karşılanmış sayılır** (ikinci faktörü
  IdP yürütür) — aksi hâlde kurumsal müşteri iki ayrı MFA'ya zorlanırdı.
- **İstemci sırrı** platform panelinde **maskeli** döner (`platform/guvenlik_ayar.py`);
  panel maskeyi geri gönderirse sunucu mevcut sırrı korur. Denetim izine düz metin yazılmaz.

**⚠️ Canlı IdP doğrulaması HÂLÂ BEKLİYOR.** Akış uçtan uca sahte IdP ile testlidir (mutlu
yol, yanlış nonce, süresi geçmiş token, yanlış audience/issuer, izinsiz alan adı, çapraz
tenant, replay, anahtar rotasyonu, saat kayması). Gerçek **Azure AD / Google Workspace**
denemesi yapılmamıştır; doldurulacak yapılandırma `docs/uyum/sso-kurulum.md`'dedir.
İlk canlı denemede claim adları farklı çıkarsa **kod değişikliği gerekmez**: `debug_claim_log`
açılır, ham claim'ler sunucu loguna yazılır, `claim_eslemesi` panelden düzeltilir.

### 4. Oturum & cihaz yönetimi

`oturumlar` tablosu refresh `jti` başına bir satır (IP + user-agent + son kullanım + bitiş).
Redis **anlık zorlama**, DB **listeleme ve adli iz** kaynağıdır — ikisi birbirinin yerine
geçmez. Rotasyonda satır yeni `jti`'yi devralır (cihaz geçmişi kopmaz). Uzaktan sonlandırma
Redis iptali + `iptal=True` işaretler. `jti` istemciye sızdırılmaz; yönetim `id` üzerinden.

### 5. Denetim kaydı görünürlüğü

`GET /denetim-kayitlari` (`denetim:oku`) — kullanıcı/kaynak/eylem/tarih filtreli, sayfalı;
`/kaynaklar` filtre seçeneklerini verir. **Append-only garantisi DB tarafında**: migration
`d8f3a6c1e592` UPDATE/DELETE'i engelleyen trigger kurar — uygulama hatası ya da ele geçirilmiş
bir oturum bile geçmişi düzeltemez. Ekranda hiçbir düzenleme/silme aksiyonu yoktur.

`denetim:oku` **`izleyici` rolüne otomatik verilmez**: adli iz hassas kişisel veri içerir,
geniş salt-okunur role dağıtılmaz (`_OKU_IZINLERI` kümesinden çıkarıldı).

### 6. KVKK paketi

- **Kişi bazlı ihraç** (`POST /kvkk/ihrac` → 202 → MinIO → 409-korumalı indirme; S14/S17
  deseni). Eksiksizlik **keşfe** bağlıdır: tenant şemasında `%kullanici_id` / `%personel_id`
  desenli TÜM kolonlar `information_schema`'dan bulunur → gelecekte eklenen modüller
  **otomatik** kapsanır (S17 dersi: statik liste eskir).
- **Anonimleştirme** tek transaction'da: kimlik alanları maskelenir, denetim izinin adli
  çekirdeği (eylem/kaynak/zaman) korunur. Geri alınamaz olduğu için `onay="ANONIM"` şartı
  (S17 slug-yazarak-onay deseni).
- **Rıza/aydınlatma** `consent_kayitlari` append-only: geri çekme yeni satırdır (`kabul=False`),
  geçmiş silinmez — ispat yükü şirkettedir.

## Sonuçlar

- Migration `d8f3a6c1e592` (tenant): `kullanici` 2FA kolonları + `kurtarma_kodlari` +
  `oturumlar` + `kvkk_ihraclari` + `consent_kayitlari` + denetim append-only trigger;
  `a9d2e6f4c318` (public): `tenant.guvenlik_ayarlari`. Fan-out up/down testli.
- Yeni izinler `denetim:oku`, `kvkk:yonet`; yeni rol `uyum`. **Yeni izin kodu mevcut
  tenant'lara otomatik inmez** → canlı tenant'larda idempotent provizyon yeniden koşulmalıdır
  (S16 dersi).
- Yeni bağımlılıklar: `pyjwt[crypto]` (RS256 id_token doğrulaması) ve `httpx` çalışma
  zamanına alındı (önce yalnız test bağımlılığıydı).
- **Yan bulgu (düzeltildi):** Alembic `env.py` `fileConfig`'i varsayılan
  `disable_existing_loggers=True` ile çağırıyordu. Migration **süreç içinde** de koştuğu için
  (S17 senkron tenant provizyonu) platform panelinden tenant açıldıktan sonra API'nin tüm
  `app.*` logger'ları kalıcı olarak susuyordu. İki `env.py`'de `disable_existing_loggers=False`
  yapıldı; regresyon testi `test_s2_provizyon.py`'de.

## Sertleştirme eki (2026-07-30, inceleme sonrası)

S23 kapanış incelemesinde dört madde eklendi:

1. **İzin sürüklenmesi sistemik olarak kapatıldı.** Yeni izin kodlarının mevcut tenant'lara
   elle taşınması (S16 ve S23'te yapıldı) unutulmaya açıktı. `control_plane/uzlastirma.py`
   katalog ↔ şema uzlaştırmasını yapar ve **migration fan-out'unun ardından otomatik koşar**
   (`tenant_yukselt_tum(uzlastir=True)`); provizyon da aynı fonksiyonu kullanır (tek doğruluk
   kaynağı). Yalnız eklemelidir: katalog dışı izin/rol silinmez. CI'da kalıcı sözleşme testi:
   *hiçbir tenant'ta katalog izni eksik olamaz*.
2. **Ham claim logu süreli.** `debug_claim_log` artık `debug_claim_log_bitis` damgası olmadan
   çalışmaz (elle JSONB düzenlemesiyle kalıcı PII loglaması açılamaz); pencere 60 dk sonra
   kendiliğinden söner, ilgisiz ayar düzenlemesi pencereyi uzatmaz, açma/kapama
   `sso_debug_ac`/`sso_debug_kapat` olarak platform denetim izine yazılır.
3. **İhraç artefaktı sertleştirildi.** İçerik zaten **presigned URL ile değil**, kimlik
   doğrulamalı uçtan akıyordu (bu bilinçli bir karar; sözleşme testiyle korunuyor: nesne
   deposunda imzalı URL yüzeyi belirirse test kırılır). Eklenenler: **7 günlük saklama
   süresi** + süresi dolunca artefaktın silinmesi ve **410** dönmesi (kayıt satırı denetim
   için kalır), kenar-tetikli `POST /kvkk/ihraclar/temizle` taraması ve **her indirmenin**
   denetim izine yazılması (kim + kimin verisi + kaçıncı indirme). Not: indirme "tek
   kullanımlık" YAPILMADI — yetkili kullanıcının aynı dosyayı tekrar indirmesi meşru bir
   ihtiyaç; kontrol tek-kullanım değil, **süre + denetim + yetki**dir.
4. **PKCE açıkça test edildi.** Önceden PKCE yalnız saf birim düzeyinde ve sahte IdP'nin
   mutlu-yol zorlamasıyla kapsanıyordu. Eklenen iki test: akışın ürettiği `code_challenge`
   ile token değişiminde **gerçekten gönderilen** `code_verifier`in eşleştiği; ve
   doğrulayıcı bozulduğunda (çalınmış kod senaryosu) IdP'nin `invalid_grant` dönmesi
   üzerine uygulamanın temiz 4xx verip **oturum açmadığı/kullanıcı yaratmadığı**.

Migration `e5b1c7d4a238` (tenant): `kvkk_ihraclari.gecerlilik_bitisi` + `indirme_sayisi`;
mevcut "hazir" kayıtlara oluşturma anından itibaren saklama penceresi **backfill** edilir.

### İnceleme düzeltmeleri (aynı gün)

- **Yetki restorasyonu yasağı.** İlk uzlaştırma sürümü rol izin kümesini katalogla
  *eşitliyordu*: yöneticinin bilinçli olarak kaldırdığı bir izni sessizce geri verirdi
  (denetlenemeyen yetki yükseltmesi). `rol_izin_tohumu` köken defteri eklendi
  (migration `f4c8a2e6b791`, mevcut bağlardan backfill'li): katalogdan eklenen her bağ
  kaydedilir; "defterde var ama rolde yok" = bilinçli kaldırma → **dokunulmaz**,
  `korunan_kaldirma` olarak raporlanır. "Defterde yok" = yeni sprint izni → eklenir.
- **İmha sırası tersine çevrildi.** Önce nesne silinip sonra commit ediliyordu; araya
  düşen bir çökme dosyayı yok edip kaydı `hazir` bırakırdı. Yeni sıra: DB'de işaretle →
  **commit** → nesneyi sil → anahtarı temizle. Çökme olursa anahtar kayıtta kaldığı için
  yetim nesne bulunabilir kalır ve temizleme taraması onu toplar (tarama artık kendi
  kendini onarır). **Yan bulgu:** istek içi açık `commit`, `SET LOCAL search_path`'i
  düşürüyor — commit sonrası tenant şeması yeniden kurulmalı (bu yola özgü değil, genel
  bir kural; kodda notlandı).
- **Saklama süresi gerekçelendirildi.** 7 gün, KVKK'nın 30 günlük **cevap** süresiyle
  karıştırılmamalı: ihraç yeniden üretilebilir olduğundan dosyanın diskte beklemesi
  yalnız sızıntı yüzeyi büyütür (`docs/uyum/kisisel-veri-envanteri.md`).

## Ertelenen işler

- TOTP sırrının uygulama düzeyinde şifrelenmesi (bugün tenant-izole DB'de düz base32).
- Parola **geçmişi/yaşı** politikası (bugün yalnız kompozisyon kuralları).
- SSO **oturum kapatma** (RP-initiated logout) ve SCIM ile kullanıcı senkronu.
- Denetim kaydı **saklama/arşivleme** politikası (bugün sınırsız birikir).
