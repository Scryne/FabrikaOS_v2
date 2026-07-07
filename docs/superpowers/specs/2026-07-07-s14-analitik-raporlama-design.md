# S14 Tasarım — Analitik & Raporlama (Faz 3 / Zekâ)

Plan kaynağı: `docs/yol-haritasi.md` §S14. Amaç: modüller-arası **KPI analitik panosu**
(`/analitik/kpi`) + **async rapor üretimi** (ReportLab PDF / openpyxl Excel, MinIO'ya
sürekli, indirilebilir).

## Kapsam

- **Analitik (`modules/analitik/`, migrationsız — salt-okunur toplulaştırma):**
  - `GET /analitik/kpi?gun=30` (`analitik:oku`; gun 1–365) — tek çağrıda modüller-arası
    KPI özeti:
    - `uretim`: toplam/sağlam adet, fire oranı, **dönem OEE** (bileşen toplamları →
      `oee_hesapla`, S3 ile aynı matematik), veri kaydı sayısı.
    - `makine`: toplam + durum kırılımı (calisiyor/durdu/bakimda/ariza).
    - `isemri`: açık (acik/atandi/devam_ediyor), dönemde kapanan, **ortalama kapanma
      süresi (saat)** (`kapanis_tarihi − olusturma_tarihi`).
    - `stok`: toplam aktif malzeme + kritik altındaki sayı (S9 kriteriyle aynı).
    - `kalite`: dönem kontrol sayısı + geçme oranı + açık uygunsuzluk (terminal olmayan).
    - `enerji`: dönem tüketimi **tür+birim kırılımıyla** (farklı birimler toplanmaz).
    - `isg`: dönem iş kazası sayısı.
    - `bakim`: aktif plan + **geciken** (sonraki bakım tarihi geçmiş) sayısı.
  - `GET /analitik/trend?gun=30` (`analitik:oku`) — günlük üretim serisi:
    `[{gun, toplam_adet, saglam_adet, fire_orani, oee}]` (date_trunc ile SQL'de gruplanır,
    OEE gün-bileşen toplamlarından `oee_hesapla` ile). Enerji trendi S10'daki
    `/enerji-tuketimleri/trend` (CAGG) ucundan zaten var — çoğaltılmaz.
- **Raporlama (`modules/rapor/`):**
  - **Saf üretici** `uretici.py`: `RaporIcerik` (başlık, alt başlık, kolonlar, satırlar,
    özet satırları) → `pdf_uret` (ReportLab platypus) / `xlsx_uret` (openpyxl) `bytes`.
    DB/IO'suz, birim testli (PDF `%PDF` sihirli baytı; XLSX round-trip okunur).
  - **Rapor türleri** (`birimler.py`): `uretim` (gün×makine OEE dökümü), `stok`
    (malzeme bakiye/kritik durumu), `kalite` (kontroller + sonuç), `enerji` (günlük
    tüketim, tür+birim), `isemri` (dönem iş emirleri). Biçimler: `pdf` | `xlsx`.
    Durumlar: `kuyrukta → hazirlaniyor → hazir | basarisiz`.
  - **Model** `Rapor` (`raporlar`, tenant şeması): oto kod `RP-{yıl}-{id:06d}`, tur,
    bicim, durum, `parametreler` JSONB (gun + hesaplanan aralık), `nesne_anahtari`
    (yanıt DTO'sunda **gizli**), dosya_adi, icerik_tipi, boyut, satir_sayisi, hata,
    uretim_suresi_sn, olusturan_kullanici_id. Migration down `f9b2d6e4a713`.
  - **Async üretim** — S13 süreç-içi asyncio görev deseni **yeniden kullanılır**
    (ADR-0015/0016; Celery yok): `POST /raporlar {tur,bicim,gun}` → `kuyrukta` kayıt
    commit + **202** → görev kendi oturumu + `search_path`; veriyi çeker, baytları
    `asyncio.to_thread`'de üretir, `NesneDepo`'ya `tenant_<slug>/rapor/<id>/<dosya>`
    anahtarıyla yükler (S12 soyutlaması, tenant-izole önek), kaydı `hazir` yapar +
    `rapor.hazir` gerçek-zaman olayı; hata → `basarisiz` + `hata`. Test enjeksiyonları
    `oturum_fabrikasi_ayarla` / `es_zamanli_ayarla` (S13 ile aynı imza).
  - **Uçlar:** `POST /raporlar` (`rapor:yaz`, 202), `GET /raporlar` (sayfalı,
    `rapor:oku`), `GET /raporlar/{id}` (`rapor:oku`), `GET /raporlar/{id}/indir`
    (ikili içerik + `Content-Disposition`; `hazir` değilse **409**).
- **RBAC:** izin kodları katalogda zaten var (`analitik:oku`, `rapor:oku`, `rapor:yaz`).
  Yeni rol `analist` = {analitik:oku, rapor:oku, rapor:yaz}. `izleyici` `*:oku`'ları
  otomatik alır → rapor **oluşturamaz** (görev ayrımı 403 testli).
- **Frontend:** Zekâ bölümüne iki ekran — `/analitik` (KPI kartları + günlük üretim/OEE
  trend çizgisi + dönem seçici 7/30/90 gün) ve `/raporlar` (liste + durum rozeti +
  oluştur modalı + indir; `hazirlaniyor` iken 4 sn yoklama + `rapor.hazir` canlı
  invalidate). i18n TR/EN; `modulKimlik` rotaları `zeka` hattına bağlanır.

## Kapsam dışı (bilinçli)

- Zamanlanmış (cron) rapor üretimi + e-postayla dağıtım — S19 operasyon.
- Rapor şablon tasarımcısı / özel sorgu oluşturucu; grafik gömülü PDF.
- `rapor.hazir` için outbox/webhook (S18'de olay kataloğuna eklenebilir) — UI kaygısı,
  yalnız gerçek-zaman yayını.

## Kabul kriterleri (plandan)

1. Rapor **async** üretilir (202 → arka plan görevi), MinIO'ya tenant-izole anahtarla
   yazılır, indirilebilir (bayt eşleşmesi testli).
2. Panolar doğru KPI gösterir (bilinen sentetik veriyle sayısal doğrulama testi).
3. Uçlar `analitik:oku`/`rapor:oku`/`rapor:yaz` korumalı; yetkisiz 403; tenant izole
   (B tenant'ı A'nın raporunu göremez/indiremez → 404).
4. Migration fan-out up/down testli; `raporlar` veri sözlüğünde.
