# ADR-0015: AI/ML Çekirdeği — scikit-learn + sürümlü MinIO artefaktı + süreç-içi eğitim görevi

Durum: Kabul
Tarih: 2026-07-07

## Bağlam
Faz 3 / S13, "çekirdekte yapay zeka" vaadinin ilk parçasıdır: tenant verisiyle eğitilen
dört model (kestirimci bakım, anomali tespiti, OEE tahmini, stok ihtiyaç tahmini),
`GET /tahmin/*` uçları (`ai:oku`), tahmin geçmişi ve `anomali.tespit` domain olayı.
Plandaki teknoloji: pandas feature pipeline + scikit-learn; eğitim "Celery job";
model artefaktları MinIO'da sürümlü.

Mevcut altyapı yeniden kullanılır: şema-başına-tenant + `search_path` (ADR-0003),
`NesneDepo` nesne depolama soyutlaması (ADR-0014), transactional outbox (ADR-0007),
Redis pub/sub gerçek-zaman (ADR-0009).

## Karar
- **Katmanlar saf tutulur (TDD).** `ozellikler.py` (pandas, DB'siz): üretim satırları →
  (makine, gün) OEE özetleri; bakım pencere özellikleri + `(gun, gun+ufuk]` arıza etiketi;
  OEE lag-N çerçevesi; stok günlük tüketim serisi. `modeller.py` (sklearn, IO'suz):
  RandomForestClassifier (arıza riski; tek-sınıf güvenli), IsolationForest (aykırılık),
  Ridge (özyinelemeli OEE ufku, [0,1] kırpma), malzeme-başına lineer tüketim hızı
  (kalan gün + önerilen sipariş). Hepsi `random_state=42` → **deterministik**; çıktılar
  JSON-serileştirilebilir `list[dict]`.
- **Sürümlü artefakt: joblib → `NesneDepo`.** Anahtar
  `tenant_<slug>/model/<tur>/<surum>/model.joblib` → tenant izolasyonu **anahtar önekiyle**
  (S12 belge deseni). DB'de yalnız üstveri: `model_kayitlari` (tur+surum uq; durum
  `egitiliyor→hazir|basarisiz`; tur başına tek `aktif`; metrikler/veri özeti JSONB;
  `nesne_anahtari` API'de açığa çıkmaz). Çıkarım süreç-içi sürüm önbelleğinden okur —
  anahtar sürüme bağlı olduğundan önbellek bayatlamaz.
- **🔧 Eğitim: Celery yerine süreç-içi asyncio görevi.** `POST /tahmin/egit` kaydı
  commit eder, `asyncio.create_task` ile eğitimi arka plana atar ve **202** döner; görev
  **kendi oturumunu** açar (`search_path` = tenant), sklearn fit `asyncio.to_thread`'de
  koşar, sonuç `hazir`+`aktif` (öncekiler pasiflenir) veya `basarisiz`+`hata` olur ve
  `ai.model` gerçek-zaman olayı yayınlanır. Gerekçe: kod tabanı asyncio-first (S8 worker
  deseni), dağıtım tek-düğüm compose, Celery Windows'ta resmi desteksiz (dev ortamı) ve
  ikinci bir framework + broker semantiği getirirdi. İş durumu zaten domain tablosunda
  (`model_kayitlari.durum`) izlendiğinden ayrı bir kuyruk tablosu da gerekmez. Ölçek
  gerektiğinde `egitim_planla` tek geçiş noktasıdır → arq/Celery'ye taşımak yerel bir
  değişikliktir. Zamanlanmış yeniden eğitim (beat) S14/operasyona bırakıldı.
- **Çıkarım istek anında.** `GET /tahmin/{kestirimci-bakim,oee,stok,anomali}` aktif
  modeli yükler, güncel tenant verisiyle tahmin eder ve **`tahminler`** tablosuna geçmiş
  satırı yazar (append-only; `GET /tahmin/gecmis`). Aktif model yoksa 404 ("önce eğitin").
  Model önbellekli + çerçeveler küçük olduğundan istek-anı çıkarım ms mertebesindedir.
- **`anomali.tespit` olayı.** Anomali çıkarımı ≥1 bulgu verdiğinde, tahmin satırıyla
  **aynı transaction'da** outbox olayı yazılır (govde: tahmin_id, model_surum,
  anomali_sayisi, makineler) + gerçek-zaman yayını. Webhook teslimatı S18.
- **RBAC — görev ayrımı.** `ai:oku` (çıkarım/görüntüleme; `izleyici` otomatik alır) +
  yeni **`ai:egit`** (eğitim tetikleme — hesaplama maliyeti + model değişimi yetkisi
  ayrışır); yeni rol `ai` = {ai:oku, ai:egit}.
- **Az veri dürüst şekilde başarısız olur.** `YetersizVeri` (eğitim ≥14 makine-gün /
  malzeme başına ≥3 gün) kaydı `basarisiz` yapar ve mesaj kullanıcıya `hata` alanında
  döner; sahte/uydurma tahmin üretilmez.

## Sonuçlar
- (+) Dört model tenant verisiyle uçtan uca eğitilir/çıkarım yapar; izolasyon hem şema
  (`model_kayitlari`) hem nesne anahtarı önekiyle yapısal; 32 yeni backend testi
  (283 → 315): saf çıktı doğrulama + entegrasyon (202→hazir, rotasyon, outbox, 403/404).
- (+) Artefakt deposu ADR-0014 soyutlamasını yeniden kullanır — yeni altyapı bileşeni yok;
  testler `BellekNesneDepo` ile altyapısız koşar.
- (−) Eğitim görevi API süreciyle yaşar: süreç ölürse görev kaybolur (kayıt `egitiliyor`
  kalır) ve yatay ölçekte tek işçi disiplini yoktur — pilot ölçeği için kabul edildi;
  S19 gözlemlenebilirlik + gerekirse adanmış işçi süreci ile ele alınır.
- (−) Modeller kasıtlı yalın (MVP zekâ çekirdeği): hiperparametre araması, çapraz
  doğrulama, mevsimsellik/dış değişken yok; metrikler eğitim-içi (in-sample). Model
  kalitesi iterasyonu ürünleşme sonrasına bırakıldı.
- (−) GET uçları geçmiş satırı yazar (okuma ucunda yazma yan etkisi) — plandaki uç
  sözleşmesine sadakat + denetlenebilir tahmin geçmişi için bilinçli ödün.

## Notlar
- Migration `f9b2d6e4a713` (down `e1f4a2c3b567`); 2 tablo (`model_kayitlari`, `tahminler`),
  hypertable/CAGG yok; fan-out up/down testli (`test_s13_migration.py`).
- Uçlar: `GET /tahmin/modeller`, `POST /tahmin/egit` (202), `GET /tahmin/gecmis`,
  `GET /tahmin/{kestirimci-bakim,oee,stok,anomali}`. Realtime: `ai.model`,
  `anomali.tespit`. Outbox: `anomali.tespit`.
- Yeni bağımlılıklar: `pandas>=2.2`, `scikit-learn>=1.5`, `joblib>=1.4`.
- Feature pencereleri: üretim 90g, arıza 365g, stok 90g; bakım pencere/ufuk 7g;
  OEE gecikme/ufuk 7g; anomali taraması son 14g (sabitler `service.py`).
