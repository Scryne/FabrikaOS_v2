# S13 Tasarım — AI/ML Çekirdeği (Faz 3 / Zekâ)

Plan kaynağı: `docs/yol-haritasi.md` §S13. Amaç: tenant verisiyle **eğitilen** ve **çıkarım
yapan** dört model, sürümlü model artefaktları, tahmin geçmişi ve `anomali.tespit` olayı.

## Kapsam

- **Feature pipeline (pandas, saf):** `modules/ai/ozellikler.py` — üretim/arıza/stok ham
  satırlarından model girdisi DataFrame'leri üretir. DB'siz test edilir.
- **Dört model (scikit-learn, saf):** `modules/ai/modeller.py`
  - `kestirimci_bakim` — RandomForestClassifier; makine başına "önümüzdeki 7 günde arıza"
    olasılığı (risk skoru + seviye). Girdi: son pencere OEE/duruş/fire + arıza geçmişi.
  - `anomali` — IsolationForest; makine-gün gözlemlerinde (duruş oranı, fire oranı,
    performans) aykırılık. Çıktı: aykırı gözlemler + skor.
  - `oee` — Ridge (lag-7 gecikme özellikleri); makine başına 7 günlük OEE tahmini
    (özyinelemeli).
  - `stok` — malzeme başına lineer tüketim hızı (en küçük kareler); kalan gün
    (`mevcut/günlük hız`) + önerilen sipariş miktarı (30 günlük ihtiyaç − mevcut).
  - Az veri → `YetersizVeri` (eğitim `basarisiz` olarak kayda geçer, kullanıcıya net mesaj).
  - Deterministik: `random_state=42`; çıktı doğrulama testleri sentetik veriyle.
- **Sürümlü artefakt (MinIO):** `modules/ai/artefakt.py` — joblib serileştirme ↔
  `NesneDepo` (S12 soyutlaması yeniden kullanılır). Anahtar:
  `tenant_<slug>/model/<tur>/<surum>/model.joblib` → tenant-izole. Süreç-içi
  `(slug, tur, surum)` model önbelleği.
- **Kayıt & geçmiş (tenant şeması):**
  - `model_kayitlari` (ModelKaydi): tur + artan `surum` (uq), durum
    `egitiliyor→hazir|basarisiz`, `aktif` bayrağı (tur başına tek aktif), `metrikler`
    JSONB, `veri_ozeti` JSONB, `nesne_anahtari`, `hata`.
  - `tahminler` (Tahmin): çıkarım geçmişi — tur, model_id FK, `cikti` JSONB,
    isteyen kullanıcı.
- **Eğitim = arka plan görevi:** `POST /tahmin/egit {tur}` → kayıt `egitiliyor` + **202**;
  eğitim `asyncio.create_task` ile kendi oturumunda (search_path=tenant) koşar; sklearn
  fit `asyncio.to_thread` ile. Bitince `hazir`+`aktif` (öncekiler pasiflenir) + `ai.model`
  gerçek-zaman olayı. 🔧 Plandaki "Celery" yerine süreç-içi asyncio görevi: codebase
  asyncio-first, tek-düğüm compose dağıtımı, Windows dev (Celery resmi desteklemez);
  ölçek gerekirse arq/Celery'ye geçiş yolu ADR-0015'te.
- **Çıkarım = istek anında:** `GET /tahmin/{kestirimci-bakim,oee,stok,anomali}` (`ai:oku`)
  aktif modeli yükler (önbellekli), güncel tenant verisiyle tahmin eder, `tahminler`e
  geçmiş satırı yazar. Aktif model yoksa 404 ("önce eğitin").
- **Olay:** anomali çıkarımı ≥1 aykırılık bulursa `anomali.tespit` **outbox** olayı
  (webhook S18) + gerçek-zaman yayını.
- **RBAC:** `ai:oku` (katalogda vardı) + yeni `ai:egit` (eğitim tetikleme — görev ayrımı);
  yeni rol `ai` = {ai:oku, ai:egit}. `izleyici` `ai:oku`yu otomatik alır.
- **Uçlar:** `GET /tahmin/modeller`, `POST /tahmin/egit`, `GET /tahmin/gecmis`,
  `GET /tahmin/kestirimci-bakim|oee|stok|anomali`.
- **Frontend:** "Zekâ" menü bölümü + AI Tahminleri ekranı (`/tahminler`): model durum
  kartları + Eğit (ai:egit), risk listesi, anomali listesi, OEE tahmin çizgi grafiği,
  stok kalan-gün tablosu; `ai.model`/`anomali.tespit` canlı invalidate; i18n TR/EN.

## Kapsam dışı (bilinçli)

- Zamanlanmış (cron) yeniden eğitim — S19 operasyon/S14'te ele alınabilir.
- Webhook teslimatı (S18), GPU/derin öğrenme, harici model servisi.
- Hiperparametre arama; modeller kasıtlı yalın (MVP zekâ çekirdeği).

## Kabul kriterleri (plandan)

1. Modeller tenant verisiyle eğitilir/çıkarım yapar (tenant-aware; izolasyon testli).
2. Çıktı doğrulama testi (sentetik veri → beklenen alanlar/aralıklar).
3. AI uçları `ai:oku`/`ai:egit` korumalı; yetkisiz 403; tenant izole.
4. `anomali.tespit` olayı üretilir (outbox satırı testle kanıtlı).
