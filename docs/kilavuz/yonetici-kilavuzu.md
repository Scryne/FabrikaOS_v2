# FabrikaOS yönetici kılavuzu

İki okur için: **fabrika yöneticisi** (kendi fabrikasının kullanıcılarını, rollerini,
entegrasyonlarını yönetir; uygulama içinden) ve **platform operatörü** (FabrikaOS'u kuran ve
işleten ekip; sunucu ve komut satırı). Günlük kullanım: [kullanıcı el kitabı](kullanici-el-kitabi.md).
Olay ve kesinti: [olay-mudahale.md](../operasyon/olay-mudahale.md).

## Kısım A — Fabrika yöneticisi

### A1. Kullanıcılar ve roller

Yönetim › Kullanıcılar (`kullanici:oku`; eklemek için `kullanici:yaz`). Kullanıcı e-posta, ad ve
bir ya da birden çok rolle açılır. Pasifleştirilen kullanıcı hemen giriş yapamaz; kayıtları ve
denetim izi korunur. Koltuk sayısı aboneliğinizin sınırını aşamaz (Yönetim › Abonelik & Modüller).

Varsayılan roller ve verdikleri izinler:

| Rol | Ne yapar |
|---|---|
| `admin` | Tüm izinler (53) |
| `izleyici` | Tüm modüllerde yalnız okuma; denetim kaydı ve KVKK hariç |
| `depo` | Stok ve satınalma: okuma + kayıt |
| `satinalma-onaylayan` | Satınalma talebi onayı (talebi açandan ayrı kişi olmalı) |
| `kalite`, `enerji`, `isg`, `ik`, `dokuman`, `duyuru`, `entegrasyon` | İlgili modülde okuma + kayıt |
| `ik-onaylayan` | İzin talebi onayı |
| `crm` | Firma, sözleşme ve talep: okuma + kayıt |
| `analist` | Analitik ve raporlar (rapor üretme dahil) |
| `ai` | AI tahminleri; model eğitimini başlatma (`ai:egit`) |
| `uyum` | Denetim kayıtları ve KVKK işlemleri |
| `finans` | Fatura hazırlama ve tahsilat; fatura kesemez |
| `finans-onaylayan` | Fatura kesme/iade/iptal, firmaya ödeme |
| `planlamaci` | Üretim planı: iş emri süresi ve sırası; iş emrinin kendisini değiştirmez |
| `satis` | Satış siparişi hazırlama, sevk ve kapatma; onaylayamaz |
| `satis-onaylayan` | Sipariş onayı (üretim emri + satınalma talebi açar) ve onaylı siparişi iptal |
| `esg` | Emisyon ve yoğunluk göstergeleri, emisyon faktörleri, ESG raporu |
| `kiosk` | Atölye ekranı: yalnız üretim okuma |
| `saha-cihaz` | Ağ geçidi hesabı: ölçüm gönderme (`edge`); insan kullanıcıya verilmez |
| `dis-panel` | Dış portal: bağlı olduğu firmanın kayıtlarını görür (müşteri/tedarikçi kullanıcısı) |

İlke: herkese en az yetki. Onay rolleri (`*-onaylayan`) kayıt açan rolle aynı kişide
toplanmamalıdır; ürün kişinin kendi talebini onaylamasını ayrıca engeller.

### A2. Abonelik ve modüller

Yönetim › Abonelik & Modüller: planınız, açık modüller, koltuk kullanımı. Planlar:

| Plan | Koltuk | Modüller |
|---|---|---|
| Deneme | 5 | Tümü (deneme süresince) |
| Temel | 10 | Üretim, iş emri, bakım, stok |
| Profesyonel | 50 | Temel + saha, kalite, enerji, İSG, İK, CRM, sözleşme, talep, DYS, duyuru |
| Kurumsal | Sınırsız | Tümü (AI, analitik, rapor, entegrasyon, finans dahil) |

Kapalı bir modülün menüsü görünmez ve API'si 403 döner; veriler silinmez, plan yükselince geri gelir.

### A3. Güvenlik

Kullanıcılar kendi 2FA'larını Güvenlik ekranından açar. Fabrika genelinde **2FA zorunluluğu**,
**parola politikası** (uzunluk, karmaşıklık) ve **IP izin listesi** (yalnız şu ağlardan giriş)
tenant güvenlik ayarlarıdır; platform operatörü açar (B4). Kurumsal kimlikle giriş (Azure AD,
Google Workspace, Keycloak … OIDC) için: [sso-kurulum.md](../uyum/sso-kurulum.md).

Bir çalışan ayrıldığında: kullanıcıyı pasifleştir, açık oturumlarını kapat, varsa ona ait API
anahtarlarını iptal et, zimmetlerini (Personel › Zimmetler) kapat.

### A4. Denetim kayıtları

Yönetim › Denetim Kayıtları (`denetim:oku`): kim, ne zaman, hangi kaydı, nasıl değiştirdi.
Kayıtlar değiştirilemez ve silinemez (veritabanı düzeyinde engelli). Filtrelenip CSV olarak
dışa alınabilir; bir uyuşmazlıkta ya da güvenlik olayında ilk bakılacak yer burasıdır.

### A5. KVKK

Yönetim › KVKK (`kvkk:yonet`):
- **Kişi verisi ihracı:** bir personel ya da kullanıcının tüm kayıtları tek dosyada (ilgili kişi
  başvurusu). Dosya belirli bir süre sonra kendiliğinden silinir.
- **Anonimleştirme:** kişisel alanlar geri döndürülemez biçimde silinir; istatistik için gereken
  kayıtlar (ör. üretim) kişiden koparılarak kalır.
- **Rıza defteri:** verilen ve geri alınan rızaların değiştirilemez kaydı.

Hangi verinin nerede tutulduğu: [kisisel-veri-envanteri.md](../uyum/kisisel-veri-envanteri.md).

### A6. Veri içe aktarma

Yönetim › Veri içe aktarma: firma, makine, malzeme, personel ve açılış stoğu Excel/CSV'den.
Akış **önizle → onayla**; tek satır hatalıysa hiçbir satır yazılmaz (hepsi ya da hiçbiri), hata
satır ve alan adıyla gösterilir. Şablon sütun adları ekranda indirilebilir. Pilot devreye alma
sırası: [pilot.md](../operasyon/pilot.md).

### A7. Webhooklar ve API

Yönetim › Webhooklar & API (`entegrasyon:yaz`):
- **Webhook:** seçilen olaylar (iş emri durumu, uygunsuzluk, stok hareketi …) belirttiğiniz
  adrese imzalı (HMAC-SHA256, `X-FabrikaOS-Signature` başlığı) gönderilir; başarısız teslim üstel beklemeyle
  yeniden denenir, teslimat geçmişi ekranda. İmza anahtarı yalnız oluşturulurken bir kez tam
  görünür; kaybederseniz **Anahtarı yenile**.
- **API anahtarı:** ERP/MES entegrasyonu için izin kapsamlı anahtar; yalnız oluşturulurken
  görünür, veritabanında özeti tutulur. Kullanılmayan anahtarı iptal edin.
- Geliştirici başvurusu: API portalı (`docs/api/index.html`, `python backend/scripts/api_portali.py`).

## Kısım B — Platform operatörü

Komutlar repo kökünden, uygulamayla aynı ortamda (`DATABASE_URL`, `SECRET_KEY` …) çalışır.

### B1. Ortam değişkenleri (üretimde zorunlu olanlar)

| Değişken | Not |
|---|---|
| `APP_ENV=prod` | Prod'da zayıf ya da varsayılan `SECRET_KEY` ile uygulama açılmaz |
| `SECRET_KEY` | ≥ 32 karakter rastgele; JWT imzası. Döndürmeden önce [dr.md](../operasyon/dr.md#anahtarlar-yedeğin-parçasıdır-s28) uyarısını oku |
| `VERI_SIFRELEME_ANAHTARLARI` | TOTP sırrı ve webhook imza anahtarının şifrelemesi; üretimde ayrı Fernet anahtarı ver, ayrı kasada yedekle |
| `DATABASE_URL`, `REDIS_URL` | PostgreSQL 16 + TimescaleDB; Redis 7 |
| `MINIO_*` | Belge deposu (S3 uyumlu); `MINIO_SECURE=true` |
| `MQTT_HOST`, `MQTT_PORT` | Saha ağ geçitleri için broker |
| `CORS_ORIGINS` | JSON listesi, ön yüz adresleri |
| `SENTRY_DSN`, `OTEL_ENDPOINT`, `METRIK_TOKEN` | Gözlemlenebilirlik ([gozlemlenebilirlik.md](../operasyon/gozlemlenebilirlik.md)) |

### B2. Kurulum ve güncelleme

```bash
python backend/scripts/kurulum.py                      # şemalar head'e (idempotent)
KURULUM_ADMIN_PAROLA=... python backend/scripts/kurulum.py --tenant fabrika-a \
    --ad "Fabrika A" --admin-eposta admin@fabrika-a.com.tr --plan profesyonel
python backend/scripts/platform_yonetici_olustur.py <eposta> <parola>   # ilk platform operatörü
```

Güncellemede şema değişikliği her tenant'a ayrı ayrı uygulanır ve biri diğerini durdurmaz:

```bash
python backend/scripts/goc_dagit.py --yedek-dizini /yedek/goc    # göç öncesi tenant yedeği alır
```

Çıktı tenant başına bir JSON satırıdır; `basarili: false` olan tenant eski şemada kalır ve
uygulama onun için hata vermeye devam eder; düzelt ve yalnız onu `--tenant` ile yeniden koş.
İzin kataloğu değiştiyse uzlaştırma göçle kendiliğinden yapılır; elle doğrulama:
`python backend/scripts/izin_uzlastir.py --kuru`.

### B3. Tenant yaşam döngüsü

Platform paneli (ayrı giriş, `/platform`): tenant aç, askıya al (erişim anında kesilir, veri
kalır), yeniden aktifleştir, KVKK ihracı al, kalıcı sil (geri dönüşsüz; tenant kodunun (slug) yazılarak onaylanmasını ister — silmeden önce ihraç ya da yedek alın). Plan, modül hakkı ve özellik bayrağı
değişikliği anında etkilidir; sunucu yeniden başlatılmaz. Komut satırı karşılığı:

```bash
python backend/scripts/entitlement_ayarla.py <slug> goster
python backend/scripts/entitlement_ayarla.py <slug> plan kurumsal
python backend/scripts/entitlement_ayarla.py <slug> modul ai ac
```

### B4. Tenant güvenlik ayarları

Platform paneli › Tenant › Güvenlik: 2FA zorunluluğu, parola politikası, IP izin listesi
(CIDR), OIDC SSO yapılandırması. Değişiklik platform denetim izine yazılır. IP listesini
daraltmadan önce yöneticinin bağlandığı ağın listede olduğunu doğrula; aksi hâlde kendi
erişimini kesersin (geri açmak yine platform panelinden).

### B5. Yedek, geri yükleme, staging

Ayrıntı [dr.md](../operasyon/dr.md); takvim [tatbikatlar/takvim.md](../operasyon/tatbikatlar/takvim.md).

```bash
python backend/scripts/yedek.py tumu --dizin /yedek                 # gece işi
python backend/scripts/yedek.py dogrula /yedek/demo-<zaman>.zip
python backend/scripts/yedek.py geri-yukle /yedek/demo-<zaman>.zip --evet
python backend/scripts/yedek.py tatbikat demo --dizin /yedek/tatbikat --rapor docs/operasyon/tatbikatlar
```

Şifreleme anahtarı yedeğin parçasıdır: başka bir kuruluma geri yüklenen tenant aynı anahtar
olmadan 2FA'lı kullanıcılarını içeri almaz.

### B6. İzleme ve nöbet

Grafana "FabrikaOS · SLI / SLO" panosu; hedefler [slo.md](../operasyon/slo.md), alarm başına ilk
adımlar [gozlemlenebilirlik.md](../operasyon/gozlemlenebilirlik.md), nöbet düzeni
[nobet.md](../operasyon/nobet.md). Sürüm öncesi kalite kapıları (CI): test, tip, lint, bandit,
pip/npm audit, mutasyon testi (eşik %90), sertleştirme taraması (0 sunucu hatası), SBOM.
