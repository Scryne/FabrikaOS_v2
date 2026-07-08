# ADR-0016: Analitik & Raporlama — salt-okunur KPI toplulaştırma + süreç-içi async rapor üretimi

Durum: Kabul
Tarih: 2026-07-08

## Bağlam
Faz 3 / S14: yöneticiye tek bakışta işletme durumu (**KPI analitik panosu**) ve
paylaşılabilir çıktı (**PDF/Excel rapor**). Plandaki teknoloji: `/analitik/kpi` uçları;
rapor üretimi "async job" ile ReportLab (PDF) + openpyxl (Excel); çıktı MinIO'ya yazılır
ve indirilebilir.

Mevcut altyapı yeniden kullanılır: şema-başına-tenant + `search_path` (ADR-0003),
`NesneDepo` nesne depolama soyutlaması (ADR-0014), süreç-içi asyncio arka plan görevi
deseni (ADR-0015), OEE saf hesabı (ADR-0006), Redis pub/sub gerçek-zaman (ADR-0009).

## Karar
- **Analitik = migrationsız, salt-okunur toplulaştırma.** `modules/analitik/` tablo
  eklemez; mevcut modül tablolarına SQL toplama sorguları atar (`repository.py`) ve
  türetimi saf katmanda yapar (`hesap.py`). `GET /analitik/kpi?gun=` tek çağrıda
  üretim/makine/iş emri/stok/kalite/enerji/İSG/bakım KPI'ları döner;
  `GET /analitik/trend?gun=` günlük üretim/OEE serisi verir. Enerji trendi S10'daki
  continuous aggregate ucundan servis edilir — çoğaltılmaz.
- **Dönem OEE = S3 matematiğinin toplamlara uygulanması.** Bileşenler SQL'de toplanır
  (`Σplanlanan, Σduruş, Σadet, Σsağlam, Σ(ideal_çevrim×adet)`); `hesap.donem_oee`
  adet-ağırlıklı ortalama çevrimle `oee_hesapla`'yı (ADR-0006) çağırır → satır-bazlı
  hesapla birebir aynı sonuç, ikinci bir OEE tanımı türememiş olur.
- **Rapor üretimi = ADR-0015 süreç-içi görev deseninin yeniden kullanımı.**
  `POST /raporlar {tur, bicim, gun}` → `kuyrukta` kayıt + commit + **202**; görev kendi
  oturumunu açar (`search_path` = tenant), durum `hazirlaniyor`a çekilir, tür-bazlı
  satırlar sorgulanır, baytlar `asyncio.to_thread`'de üretilir (CPU-bağımlı ReportLab/
  openpyxl event loop'u bloklamaz), `NesneDepo`'ya yazılır ve kayıt `hazir` olur; hata →
  `basarisiz` + `hata` mesajı. Her iki sonda `rapor.hazir` gerçek-zaman olayı yayınlanır.
  Celery yine reddedildi (gerekçeler ADR-0015; `uretim_planla` tek geçiş noktası).
- **Saf üretici katmanı.** `uretici.py` DB/IO'suz: biçimden bağımsız `RaporIcerik`
  (başlık + kolonlar + satırlar + özet) → `pdf_uret` (ReportLab platypus, yatay A4,
  tekrar eden tablo başlığı) / `xlsx_uret` (openpyxl, sayılar sayı olarak). Birim testler
  PDF sihirli baytını ve XLSX round-trip'ini doğrular. Beş rapor türü: `uretim`
  (gün×makine OEE dökümü), `stok` (bakiye/kritik), `kalite` (kontroller), `enerji`
  (günlük tür+birim), `isemri` (dönem iş emirleri).
- **Rapor dosyası DB'de değil nesne deposunda.** Anahtar
  `tenant_<slug>/rapor/<id>/<dosya>` → tenant izolasyonu anahtar önekiyle (S12/S13
  deseni). DB'de yalnız üstveri (`raporlar`: kod `RP-{yıl}-{id:06d}`, durum
  `kuyrukta→hazirlaniyor→hazir|basarisiz`, parametre penceresi kayda dondurulur,
  boyut/satır sayısı/üretim süresi; `nesne_anahtari` API yanıtında açığa çıkmaz).
  İndirme `GET /raporlar/{id}/indir` ikili içerik döner; `hazir` değilse **409**.
- **`rapor.hazir` outbox'a yazılmaz.** Olay UI tazeleme kaygısıdır (liste invalidate);
  webhook kataloğuna almak gerekirse S18'de outbox'a bağlanır. `anomali.tespit`
  (iş olayı) ile bilinçli ayrım.
- **RBAC — görev ayrımı.** `analitik:oku` + `rapor:oku` (izleyici otomatik alır) ve
  `rapor:yaz` (üretim tetikleme — depolama/CPU maliyeti yetkisi ayrışır); yeni rol
  `analist` = {analitik:oku, rapor:oku, rapor:yaz}.

## Sonuçlar
- (+) Pano tek istekle beslenir (8 KPI bloğu); sayısal doğruluk izole `kpi` tenant'ında
  elle hesaplanan değerlerle birebir test edilir; izolasyon + RBAC 403 testli.
- (+) Rapor hattı uçtan uca: 202 → arka plan → MinIO → indirme bayt eşleşmesi testli;
  35 yeni backend testi (337 → 372). Yeni altyapı bileşeni yok.
- (−) KPI sorguları her istekte canlı toplar (önbellek yok); pilot veri hacminde ucuz,
  büyüyünce Timescale continuous aggregate/materialized view S19 performans işidir.
- (−) Rapor görevi API süreciyle yaşar (ADR-0015 ile aynı ödün): süreç ölürse kayıt
  `kuyrukta/hazirlaniyor` kalır; S19'da gözlemlenebilirlik + gerekirse adanmış işçi.
- (−) Rapor içeriği tablo+özet düzeyinde (grafik gömülü PDF yok); zamanlanmış üretim ve
  e-posta dağıtımı S19 operasyon kapsamına bırakıldı.

## Notlar
- Migration `b4e8f2a6c159` (down `f9b2d6e4a713`); 1 tablo (`raporlar`), hypertable yok;
  fan-out up/down testli (`test_s14_migration.py`).
- Uçlar: `GET /analitik/kpi`, `GET /analitik/trend`, `POST /raporlar` (202),
  `GET /raporlar`, `GET /raporlar/{id}`, `GET /raporlar/{id}/indir`. Realtime: `rapor.hazir`.
- Yeni bağımlılıklar: `reportlab>=4.2`, `openpyxl>=3.1`.
- Rapor penceresi kayda dondurulur (`parametreler.baslangic/bitis`) → aynı kayıt yeniden
  üretilse aynı dönemi anlatır (denetlenebilirlik).
