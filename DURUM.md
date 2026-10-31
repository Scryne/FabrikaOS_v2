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
