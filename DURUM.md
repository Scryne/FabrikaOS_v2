# DURUM — FabrikaOS_v2 — çok kiracılı MES+ERP

> **Ne bu dosya:** sertifika değil **envanter**. Ölçülen gerçek durum; "çalışmıyor" yazan satır
> kusur değil, kayıt. Kapanış standardı: `ScryneOS/🎯 100-Command-Center/Kapanis-Standardi.md`

**Ölçüm tarihi:** 2026-09-26 (önceki: 2026-08-27)
**Tek cümle:** Backend 667 + frontend 214 test yeşil, CI 07-30'dan beri ilk kez tam kapıdan
geçecek durumda; demo tenant tüm modülleriyle dolu ve kendini bugüne getiriyor.

## Ne çalışıyor (ölçüldü)

- **Backend:** 667 test (birim + gerçek PostgreSQL/TimescaleDB entegrasyon), MinIO kapalıyken
  de 657/657 → testler dış servise bağlı değil. `ruff`, `ruff format`, `mypy` temiz, `pip-audit` 0.
- **Frontend:** 214 test, `tsc --strict`, ESLint, Prettier, Vite 8 derlemesi temiz. `npm audit`
  yüksek/kritik 0 (kalan 2 orta: react-router 6, bkz. README güvenlik notları).
- **CI benzetimi:** `node:22` konteynerinde temiz `npm ci` + tam frontend kapısı geçti.
- **Docker:** API imajı derleniyor (`.dockerignore` README'yi dışlıyordu → düzeltildi);
  compose'da `bildirim` ve `webhook-relay` süreçleri var.
- **Demo:** `demo` tenant — 12 makine, 14+ gün üretim, iş emirleri, bakım, stok, satınalma,
  kalite/CAPA, enerji, İSG, İK, CRM, DYS, duyuru, vardiya/duruş, ürün/reçete + lot
  izlenebilirliği, 3 rapor, 144 bildirim, 3/4 AI modeli eğitilmiş.
- **Arayüz:** 43 tenant + 6 platform ekranı masaüstü ve mobilde (390 px) yatay taşmasız ve konsol
  hatasız; 10 etkileşimli görünüm (lot sorgusu, harita, takvim, Pareto, kanban, komut paleti) hatasız.

## 2026-11-03 — Kabuk yüksekliği + okunur adlar (arayüz düzeltmesi)

- **Kabuk:** yan menü uzunluğu (≈2777 px) her sayfanın belge yüksekliğini o boya çekiyordu; kısa
  sayfalarda altı boş bir kaydırma çıkıyordu. Menü artık görünüm yüksekliğine yapışık ve kendi içinde
  kayıyor; seçili öğe menüde görünüme getiriliyor. Ölçüm (demo, 1440 px): izin talepleri 2777 → 900 px,
  pano 2777 → 1875 px. 390 px çekmece, `lg` altı daraltma ve kiosk (kabuksuz) değişmedi. Yerleşim
  jsdom'da ölçülemediği için `e2e/kabuk.spec.ts` (4 test; düzeltme geri alınınca 4'ü de düşüyor).
- **Ham id / ham enum taraması** (52 menü ekranı × ilk 3 satırın çekmecesi × sekmeler × pano görünümü,
  1440 ve 390 px, admin + İK + İK onaylayan + CRM rolleri). Düzeltilen: izin talebi personeli `#6`
  (liste, pano kartı, çekmece; backend `personel_ad`, sayfa başına tek sorgu), talep ve sözleşme
  çekmecesinde firma/atanan `#id`, iş emri kanbanında atanan `#id`, fatura firma süzgecinde `#id`
  titremesi, enerji tablosunda çıplak makine id'si (backend `makine_kod`, tek sorgu), malzeme
  hareketlerinde `transfer_giris/transfer_cikis` (eksik çeviri), bildirim tercihlerinde 4 olayın eksik
  çevirisi, denetim kayıtlarında kaynak/eylem kodları, onay kutusunda izin türü (`yillik`).
- **Korunan:** adlar mevcut izin kapılarından gelir (personel adı `ik:oku`'lu izin uçlarında; kullanıcı
  adı `kullanici:oku`, firma adı `crm:oku` ile ön yüzde). İzin yoksa kayıt numarası görünür, yeni yetki
  açılmadı. İzin yanıtı yalnız ad/soyad taşır (TC hiçbir biçimde dönmez; test). N+1 testi: satır sayısı
  5 katına çıkınca SQL sayısı değişmiyor; satır başına sorguya çevrilince test düşüyor.
- **Bilinçli bırakılan:** denetim kaydındaki kayıt no ve ham JSON gövdesi (adli iz), KVKK ihracındaki
  kişi no (veri minimizasyonu; uyum rolü ad görmez), bildirim tercihlerinde olayın teknik kodu (alt
  satır), içe aktarma şablonunun CSV sütun adları, webhook olay kodları (geliştirici sözleşmesi).

## 2026-11-01 — S32 ESG & sürdürülebilirlik (ADR-0051)

- Kapsam 1/2 emisyon ham enerji tüketiminden, İstanbul saatine göre dönemlere; faktörsüz tüketim ayrı. 10 birim +
  4 entegrasyon testi (bilinen seri: pencere ortasında faktör değişimi, gece yarısı sınırı, aylık dönem başı
  faktörü); `hesap.py` mutasyon %100; üç koruma sökülünce testler düşüyor (3/3).
- Varsayılan faktörler araştırmayla birincil kaynaktan (ETKB 2023 tüketim noktası 0,469 kg CO2e/kWh; IPCC ×
  ETKB alt ısıl değer → doğalgaz 1,928 kg CO2e/Sm³); belirsizlikler ADR-0051 §2'de.
- Canlı (dev demo): 30 gün 2,657 t CO2e, elle doğrulandı (2.958,4 kWh × 0,469; 658,3 m³ × 1,928); basınçlı hava
  faktörsüz uyarıda. PDF önizlemesi Türkçe karakterli; yoğunluk sütunu ilk turda 2 basamağa yuvarlanıp
  0,0261 → 0,03 oluyordu → 4 basamak. Dev'de MinIO yok: rapor yükleme adımı bütün türlerde başarısız (bilinen).

## 2026-11-01 — S31 satış & sipariş → MRP (ADR-0050)

- Sipariş → MRP → üretim iş emri + satınalma talebi zinciri: 18 birim + 6 entegrasyon testi; `mrp.py` ve
  `durum.py` mutasyon %100. Tetik tekilliği, görev ayrımı ve "siparişin kendi tetiklerini hesaptan
  çıkarma" tek tek sökülünce testler düşüyor (3/3).
- Canlı (dev, demo tenant, gerçek tarayıcı): satış temsilcisi formdan sipariş açtı (onay düğmesi yok);
  satış onaylayan onayladı → 2 üretim emri + 4 eksik malzemelik satınalma talebi, "Açılan işler"de
  bağlantılı. İkinci siparişin MRP'si ilkinin ayırdığı 560 kg sacı ve açtığı talebi doğru gösteriyor.
  1440/390 taşmasız.
- Bulunup düzeltilen: (1) MRP, onaydan sonra siparişin kendi iş emrini "ayrılmış", kendi talebini "açık
  tedarik" sayıyordu (ihtiyaç iki kez düşerdi); (2) firma tipi `her_ikisi` olan müşteri reddediliyordu;
  (3) satış rolleri üretim hattını seçemiyordu (`uretim:oku` eksikti, seçici ham id gösteriyordu);
  (4) S30 demo tohumu operasyon işlerine (kesim/büküm/boya) ürün bağlıyordu — S24'te her biri
  kapanışta reçeteyi ayrıca düşerdi; MRP'de "ayrılmış" 10 kat şişiyordu. Ürün bağı kaldırıldı.

## 2026-11-01 — S30 üretim planlama & çizelgeleme (ADR-0049)

- Makine başına sonlu kapasite çizelgesi (vardiya pencereleri, EDD, devam eden önce, elle süre/sıra);
  kapasite aşımı saf EDD çizelgesinden (Jackson) ayrılır, elle sıradan doğan gecikme ayrı işaretlenir.
  13 birim + 3 entegrasyon testi (+6 ön yüz); çizelge çekirdeği mutasyon %84,6 (kalan 10 mutant eşdeğer: sıralama
  anahtarı sabit kaydırmaları, 1e-9 toleransı).
- Canlı: Üretim planı ekranı 3 durumu gösteriyor (LAZER-1 kapasite aşımı 6 sa, MONTAJ-1 sıra kaynaklı
  13 sa, diğerleri zamanında); çekmeceden sıra kaldırılınca acil iş öne geçip zamanında oldu. Gün adları
  ilk turda İngilizceydi (dayjs yerel ayarı yok) → `Intl.DateTimeFormat(i18n.language)`.
- Tam takım yerelde ilk iki koşuda bir testte kilitlendi: `REDIS_URL` verilmemişti, bildirim testleri
  çalışmayan 6379'u bekliyordu. Doğru adresle 852/852 (S31 öncesi). Redis yokken takılmak yerine hızlı
  düşmesi ayrı bir iyileştirme.

## 2026-11-01 — S29 finans & muhasebe (ADR-0048)

- Backend 819 test yeşil (S29: 11 entegrasyon + 17 birim), ön yüz 236. ruff, mypy, tsc, eslint temiz.
- Eşzamanlı iki tahsilat açık tutarı aşamıyor; aynı Idempotency-Key ikinci ödeme açmıyor; hazırlayan
  faturasını kesemiyor. Fatura satır kilidi, idempotency ve görev ayrımı tek tek kaldırıldığında ilgili
  testler düşüyor (3/3); finans saf çekirdeği mutasyon %100.
- Canlı (dev, demo tenant): Onaylarım'da onay bekleyen fatura görünür → kesildi → detaydan tahsilat
  (açık tutar dolu gelir) → kapandı. 4 ekran 1440/390 taşmasız, konsol temiz. İlk turda pano
  KPI'larında `₺` alt satıra düşüyor ve alacak tablosu sığmıyordu → kısa tutar biçimi, sade tablo.
- Demo tohumu taze tenant'a baştan basıldı (12 fatura, 5 tahsilat/ödeme, çıkış 0).
- Bilinçli sınır: genel muhasebe (yevmiye, mizan) ve doğrudan GİB bağlantısı yok; e-Fatura entegratör
  üzerinden (iskelet uçlar hazır).

## 2026-11-01 — S28 kurumsal güvence (ADR-0047)

- Backend 791 test yeşil (S28: +44), ön yüz 230. ruff, mypy temiz; gitleaks çalışma ağacı ve geçmiş temiz.
- Mutasyon testi 9 saf çekirdekte %93,4 (başlangıç %57,7); CI eşiği %90.
- Schemathesis: ilk koşu 88 uçta 500 (76 GET + 12 yazma). Merkezi SQLSTATE sınıflamasından sonra
  277 uç, 13.098 örnek, 0 sunucu hatası (`backend/scripts/sertlestirme.py`, CI `sertlestirme` işi).
- Dayanıklılık: Redis, MinIO, MQTT ve DB kesintisi 6 testle; düzeltmeler geri alınınca 4/4 düşüyor.
  Depo yokken belge yüklemesi 21 sn → 503 (SDK varsayılan yeniden denemeleri × 7 sn DNS); bağlantı
  denemesi bire indirildi.
- TOTP sırrı ve webhook imza anahtarı veritabanında Fernet ile şifreli; göç up/down testli; dev veritabanı
  göçe getirildi.
- Kılavuz iddiaları koddan doğrulanırken iki kusur: kişi kendi satınalma/izin/mesai talebini onaylayabiliyordu
  (artık 403; 13 test ve demo tohumu onaycıya taşındı) ve rapor hazır bildirimi hiç üretilmiyordu. Demo tohumu
  taze bir tenant'a baştan sona basıldı (çıkış 0).
- Doküman: olay müdahale, nöbet, tatbikat takvimi, sertleştirme raporu, kullanıcı el kitabı, yönetici
  kılavuzu, API portalı, ISO 27001 güncel + ISO 9001. Bilerek ertelenen: imaj imzalama, OIDC client
  secret şifrelemesi.

## 2026-11-01 — S27-B dışa aktarma, sipariş PDF'i, yazdırma, erişilebilirlik (ADR-0046)

- Ön yüz 229 test yeşil (dışa aktarma çekirdeği 4: CSV biçimi, formül etkisizleştirme, sütun
  türetme, kimlik sütunu). Backend: sipariş PDF'i 3 test (biçim, eksik fiyat, uç yetkisi + denetim).
- Canlı: malzeme listesinden Excel ve CSV gerçekten indirildi ve açıldı (12 kayıt + başlık;
  "Ad;Kod;Mevcut;Kritik eşik;Durum"). İlk denemede "Ad" sütunu kodu gösteriyordu → kimlik kuralı.
  Sipariş PDF'i görüntüye çevrilip incelendi (Türkçe karakter, toplam, eksik fiyat dipnotu).
  Yazdırma: ilk baskıda başlık ve KPI'lar beyaz kâğıtta görünmüyordu → renk değişkenleri baskıda
  yeniden tanımlandı.
- axe-core (WCAG 2.1 AA) 11 ekran: önce her sayfada 12+ kontrast, adsız grafik/seçici/ilerleme;
  sonra 11/11 temiz.
- Bulunan kusur: takvim günü 14 yerde UTC'den alınıyordu (TR 00:00–03:00 arası bugünün tarihli
  kalibrasyonu "gelecek tarih" sayılıyordu). `core.zaman.is_gunu()` (Europe/Istanbul) ile düzeltildi.

## 2026-11-01 — S27-A onay kutusu, içerik araması, code-split (ADR-0045)

- Backend: onay kutusu ve arama testleri 2 yeni (izin/modül süzgeci, görev ayrımı, kalemdeki ucun
  çalışması, RBAC, kiracı izolasyonu, joker kaçışı); iki mutasyon yakalandı.
- Ön yüz: Onaylarım (2) ve ⌘K içerik araması (1) bileşen testi; menü testleri yeni izinsiz girdiye
  göre güncellendi. Ana JS parçası 863 kB → 246 kB (gzip 226 → 78 kB), 66 sayfa ayrı parçada.
- Canlı (demo): Onaylarım 5 kalem (1440/390 taşma 0), ⌘K "rulman" → malzeme + iş emri grupları,
  `?kayit=1` çekmeceyi açıyor ve kapanınca URL'den siliniyor.
- Mobil uygulama (M0–M5) Scryne'ın kararıyla kapsam dışı (2026-11-01).

## 2026-11-01 — S26-B İSG + İK kurumsal tamamlama (ADR-0044)

- Backend 741 test yeşil (MQTT hariç): S26-B birim 7 (hakediş tablosu, artık gün, yaş alt sınırı,
  matris durumları), entegrasyon 7, göç up/down 1 (S26-A ve S26-B ayrı ayrı geri alınıp yeniden
  kuruluyor). Mutasyonlar yakalandı: bakiye kapısı, `FOR UPDATE` kilidi (eşzamanlı iki onaydan
  biri 409), açık zimmet kuralı, org döngü kontrolü.
- Ön yüz 223 test yeşil (iki ardışık tam koşu). `KvkkSayfasi` testindeki zaman aşımı giderildi:
  büyük sayfada `getByRole` ve karakter gecikmesi paralel koşuda 15 sn'yi aşıyordu; aynı öğeler
  ucuz sorguyla bulunuyor, doğrulamalar değişmedi.
- Canlı (demo tenant, tohum gerçek API'den): org şeması (genel müdür + 3 yönetici), eğitim matrisi
  13 geçerli / 3 yaklaşıyor / 5 eksik-geçmiş, KKD eksikleri, iki tatbikat (biri gecikmiş plan),
  yarım işe giriş listesi, kazadan açılmış CAPA. Ekran turu 1440/390: 11 görünüm, taşma 0,
  konsol hatası 0.
- Demo tohumunda işe giriş tarihleri en az 1 yıl öne alındı: yeni bakiye kapısı 90 günlük
  personelin 5 günlük yıllık iznini (doğru olarak) reddediyordu.

## 2026-11-01 — S26-A kalite olgunluğu: SPC + kalibrasyon (ADR-0025)

- Backend 726 test yeşil (MQTT gidiş-dönüşü hariç, Docker gerekiyor); S26-A'nın 18'i: SPC saf
  fonksiyonları 10, uç testleri 8. Mutasyonlar (ihlal tamamlayan nokta, kalibrasyon kapısı,
  tedarikçi tipi) yakalandı. Ön yüz: SPC kartı bileşen testi 2/2, tsc/ESLint/Prettier temiz.
- Canlı (demo tenant): kalibrasyonsuz cihazla ölçüm 422 `KALIBRASYON_GECERSIZ`; 25 alt grubun son
  dördünde kayma → 4 ihlalli ölçüm, 8 kural ihlali; 180 günlük cihaz 11 gün kala "yaklaşıyor".
- Ekran turu 1440/390: kontrol planları, plan detayı, iki SPC kartı, cihaz listesi, iki cihaz
  detayı, plan formu, uygunsuzluk formu → taşma 0, konsol hatası 0.
- Bulunan eski boşluk: sözleşme bitişi ve SLA taramaları hiç zamanlanmamıştı (yalnız elle tetiklenen
  uç). Üçü bildirim işçisinde 15 dk aralıkla koşuyor.
- Bilinen: tam vitest koşusunda `KvkkSayfasi` testi yük altında bir kez zaman aşımına düştü, tek
  başına 7/7 geçiyor (S26-A'dan bağımsız, izleniyor).

## 2026-11-01 — S22 sertleştirme ve kapasite (ADR-0043)

- Bandit: yüksek 0, orta 22 (hepsi B608, tek tek incelendi: beyaz liste / doğrulanmış şema adı /
  katalog tablo adı), CI kapısı orta ve üstü.
- k6 (`perf/k6/nfr01_liste.js`, 16 uç): 1 işçi 20 kullanıcı p95 181 ms ✅, 50 kullanıcı 469 ms ❌
  (kuyruk, ~125 istek/sn'de doyuyor); 4 işçi 50 kullanıcı p95 154 ms ✅, 340 istek/sn.
- Prod katmanı 4 işçi + Prometheus çok süreç modu; canlıda 4 işçiye dağılan 200 istek `/metrics`'te
  200 olarak toplandı. Ölçüm sırasında bulunan tuzak: Windows'ta öldürülen üst sürecin yetim
  işçileri portu dinlemeye devam edip eski kodla cevap veriyordu.
- Açık: ZAP/pentest, 50 tenant yük testi, UAT ve `v1.0.0` (pilot gerekir).

## 2026-11-01 — S21 tohumlama + veri içe aktarma (ADR-0042)

- `scripts/kurulum.py`: public + tenant başına göç + provizyon; iki kez koşturuldu, ikincisi temiz.
- Veri içe aktarma (firma, makine, malzeme, personel, açılış stoğu): önizle → hepsi-ya-hiç uygula,
  anahtarla idempotent; `;`/cp1254/XLSX ve `1.234,5`; TCKN sağlaması, yanıtta değer yok; açılış stoğu
  hareketle (ikinci yükleme stoğu ikiye katlamaz). Backend 12 test (5/5 mutasyon), FE 3 + menü.
- Ekran turu: 1440 ve 390 px taşmasız (390'da 306 px taşma bulundu: ızgara `minmax(0,1fr)`),
  hatalı dosyada uygula kapalı, temiz dosya uygulandı, yeni makine listede; konsol 0.
- Demo seed'i saate bağlı kırılıyordu: gecikmiş siparişin teslim tarihi "şimdi − 20 sa" idi; yerel
  20:00'den önce sipariş gününden önceye düşüp reddediliyordu (gece yarısından sonra yakalandı).
- Açık: pilot fabrika (müşteri gerektirir), `docs/operasyon/pilot.md`.

## 2026-10-31 — S20 yedekleme/DR + staging (ADR-0041)

- Tenant yedeği/geri yüklemesi (`app/operasyon/yedek.py`, `scripts/yedek.py`): yapı göçten, veri
  ikili COPY; geçici şemada doğrulanıp atomik yer değiştirir. Şema dökümü hypertable'ları boş
  yedeklerdi (chunk'lar `_timescaledb_internal`'da) — bu yüzden bu yol.
- İlk denemede gerçek şemada FK döngüsü çıktı (sıralı yükleme imkânsız) → FK'ler yüklemede
  kaldırılıp yeniden ekleniyor (bütünlük ikinci kez doğrulanıyor).
- Staging anonimleştirme (`anonim.py`), göç dağıtımı (`goc_dagit.py`), prod compose katmanı
  (`docker-compose.prod.yml`: Traefik joker TLS, WAL arşivi, yedek servisleri).
- Kanıt: 9 test (yedek 7 + dağıtım 2), 8/8 mutasyon; demo tatbikatı 67 tablo/1.927 satır
  1,9 sn; PITR tatbikatı hedef ana doğru döndü (arşiv gecikmesi = `archive_timeout`); demo staging
  kopyasında PII taraması 0 (prod 855). Prod compose Docker'da koşturulmadı.

## 2026-10-31 — S19 gözlemlenebilirlik (ADR-0040)

- `/metrics` (rota şablonu etiketli istek/süre + işçi sayaçları), Sentry (tenant/request_id
  etiketli; gövde/çerez/`Authorization`/yığın yerelleri gönderilmez), OpenTelemetry (FastAPI +
  SQLAlchemy, log satırında `trace_id`), gerçek hazırlık yoklaması (DB + Redis → 503).
- SLO-1 (%99,5) ve SLO-2 (GET p95 < 300 ms) çok pencereli yanma hızı alarmları; `promtool` birim
  testli, 6 mutasyonun 6'sı yakalandı; CI'da `gozlem-kurallari` işi.
- Canlı tur (Docker'sız, Windows ikilileri): gerçek 503 trafiği → alarm → Alertmanager → webhook;
  Grafana panosu ve Jaeger izi gerçek veriyle. Turda bulunup düzeltilen: SQLAlchemy 2.1'de
  enstrümantasyon sessizce kapalıydı; yoklama uçları SLI'yı bozuyordu; yoklama SQL'i sahipsiz iz
  üretiyordu. Testte bulunan: Sentry yığın yerelleri `Authorization` başlığını taşıyordu.
- Loki + Alloy yalnız yapılandırma (Docker'da doğrulanmadı). `docs/operasyon/`.

## 2026-10-31 — S25-B satınalma siparişi → teslim → iade

- Backend 674 test geçti (yalnız Docker isteyen MQTT turu kırmızı), ruff/mypy temiz; frontend 214,
  tsc/ESLint/Prettier temiz. Sipariş listesi/detayı, teslim ve iade pencereleri 1440 ve 390 px'te
  taşmasız, konsol hatasız.
- Demo seed: kiracı "kurumsal" planla açılıyor (önce "deneme"nin 5 koltuğuna takılıp duruyordu);
  tedarik zinciri bölümü eklendi (lokasyonlar, transfer, açık sayım, biri gecikmiş iki sipariş,
  eşleşmemiş hızlı kabul).
- Rapor PDF'leri Türkçe karakterleri kutu basıyordu (Helvetica/WinAnsi) → DejaVu Sans gömülü.
- Talep çekmecesi malzemeyi kimlik numarasıyla gösteriyordu → ad + kod.

## 2026-10-31 — Docker'sız test tabanı + S25-A

- Testler Docker'sız yerel PostgreSQL 16 + TimescaleDB + Redis'te koşuyor (`TEST_DATABASE_URL`,
  `REDIS_URL`). conftest test DB adını URL'den türetiyor: iki koşu aynı sunucuda birbirinin
  veritabanını düşürmüyor. Backend 662 geçti; tek kırmızı MQTT testi (testcontainers, Docker ister).
- S25-A: depo/lokasyon, lokasyon×lot bakiyesi, iki bacaklı transfer, sayım (delta onay, görev
  ayrımı) + üç ekran; 390 px'te taşmasız, konsol hatasız. Frontend 214 test, tsc/ESLint/Prettier temiz.

## 2026-09-26 denetiminde kapatılanlar

1. CI kırmızısı: 5 KVKK testi gerçek MinIO'ya çıkıyordu → bellek içi depo fikstürü; sözleşme
   testi gerçek depoyu sonraki testlere sızdırıyordu.
2. Beklenmeyen 500 CORS başlığı ve `x-request-id` olmadan dönüyordu (tarayıcıda "CORS hatası")
   → içteki saf ASGI hata katmanı + regresyon testi.
3. WebSocket JWT'si erişim loguna düz metin yazılıyordu → log maskeleme + test.
4. Mobilde her oturumlu sayfa +241 px yatay taşıyordu; menü içeriği itiyordu → duyarlı üst bar,
   katman çekmece; grafik eksen etiketleri üst üste biniyordu.
5. Bildirim üretici ve webhook relay compose'da yoktu (bildirim merkezi hiç dolmazdı).
6. Demo seed S24/S-VB/rapor modüllerini doldurmuyordu, "Tenant Yöneticisi" adıyla karşılıyordu
   ve zaman serisi seed anına sabitti (kiosk birkaç günde sıfıra düşüyordu).
7. 10 yüksek/kritik geliştirme bağımlılığı açığı (Vite 5→8, Vitest 2→5, Playwright 1.63),
   ECharts XSS (5→6.1); CI Node 20→22, action'lar v7, bağımlılık taraması CI'ya eklendi.
8. DESIGN.md Google DESIGN.md spec'ine çevrildi; README durumu 08-27'den bayattı.
9. Anomali bildirim yağmuru: `GET /tahmin/anomali` her görüntülemede outbox olayı yazıyordu
   (09-23'te bir saatte 49 olay → her yetkili kullanıcıya bildirim) → aynı makine kümesi 24 saat
   içinde tekrar bildirilmez (test). Başlık "AI anomali tespiti: " diye boş bitiyordu → makine
   kodları / bulgu sayısı.
10. Bildirim zili satırlarının CSS sınıfı hiç tanımlanmamıştı (tarayıcının gri butonu, okunaksız).
11. Sayfa başlığı aksiyonları ve 3 tablo (kritik stok, platform tenant/abonelik) dar ekranda
    sayfayı yatay kaydırıyordu.
12. Demo: lot üretim kayıtları (izlenebilirliğin son halkası boştu) ve makine konumları (coğrafi
    harita boştu) eklendi.

## Ne yarım / bilinçli açık

- S25 tamam (ADR-0024 "Uygulama durumu"); fatura eşlemesi ve birim dönüşümü bilinçli olarak
  sonraya. S19 (ADR-0040) ve S20 (ADR-0041) tamam; S21 ve S22'nin yazılım tarafı tamam; pilot, UAT ve GA dışa bağlı. `uretim_verileri` hypertable'ında sıkıştırma/
  saklama politikası yok (S3 notu) — yük testiyle (S22) birlikte ele alınacak.
- Stok tahmin modeli malzeme başına ≥3 günlük gerçek tüketim ister; yeni tenant'ta bekler.
- Playwright E2E CI'da değil (çalışan yığın + seed ister).
- Uzak dallar: `feat/persona-pano-landing-derinlestirme`, `feat/s18-dis-portal-webhook`,
  `feat/s6-uretim-isemri-ekranlari`, `feat/s7-gercek-zaman` — içerik main'de; silinmesi sahibin kararı.
