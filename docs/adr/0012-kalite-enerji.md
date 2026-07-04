# ADR-0012: Kalite (Tam CAPA) & Enerji (hypertable + continuous aggregate)

Durum: Kabul
Tarih: 2026-07-01

## Bağlam
Faz 2 / S10 çekirdeğin üzerine iki iş modülü ekler: **Kalite** (denetim + uygunsuzluk/CAPA)
ve **Enerji** (tüketim zaman serisi + trend). Enerji trendi için S3'te (ADR-0006) autocommit
gereksinimi nedeniyle ertelenen **continuous aggregate** kararı burada uygulanır.

Mevcut altyapı yeniden kullanılır: şema-başına-tenant + `search_path` (ADR-0003), Alembic
iki-ağaç fan-out (ADR-0004), RBAC izin/rol kataloğu (ADR-0005), TimescaleDB hypertable deseni
(ADR-0006), transactional outbox + saf durum makinesi (ADR-0007), Redis pub/sub gerçek-zaman
(ADR-0009).

## Karar
- **Tam CAPA (Uygunsuzluk).** `Uygunsuzluk` saf, DB'siz, kapsamlı birim testli durum
  makinesiyle (`kalite/durum.py`) yönetilir: `acik → kok_neden → aksiyon_plani → uygulama →
  dogrulama → kapandi` (+ her aktif aşamada `iptal`; `dogrulama → uygulama` geri dönüşü —
  doğrulama başarısız olursa uygulamaya döner). Terminal durumlardan (`kapandi`, `iptal`)
  çıkış yok. Düzeltici/önleyici aksiyonlar ayrı `CapaAksiyon` satırlarıdır (kendi durumu:
  `planlandi/tamamlandi/iptal`, n–1 uygunsuzluk). **Tüm geçişler `kalite:yaz`** ister — ayrı
  onay izni yoktur (S9 satınalma görev-ayrımından bilinçli fark; kalite süreci tek roldedir).
  `KaliteKontrol` denetim/muayene kaydıdır (makine + iş emri opsiyonel FK); `kaldi` denetim
  otomatik uygunsuzluk **üretmez** (elle, opsiyonel `kaynak_kontrol_id` bağı). Uygunsuzluk
  açılışında `kalite.uygunsuzluk` domain olayı transactional outbox'a yazılır.
- **Enerji hypertable.** `enerji_tuketim` `UretimVerisi` deseniyle TimescaleDB hypertable
  (partition `zaman`, PK `(zaman, id)`, `Identity`); `makine_id` **nullable** = tesis geneli
  tüketim. Ölçüm elle girilir (edge enerji ingestion sonraki faza bırakıldı).
- **Continuous aggregate.** `enerji_tuketim_saatlik` (saatlik `time_bucket`) materialized view
  `WITH (timescaledb.continuous, timescaledb.materialized_only = false)` + saatlik refresh
  policy. Migration'da **`op.get_context().autocommit_block()`** zorunlu — TimescaleDB CAGG'i
  ve policy'yi transaction bloğunda oluşturamaz; `search_path` env'de `SET` (session) olduğundan
  autocommit commit'inden sonra korunur → CAGG doğru tenant şemasında oluşur. Trend ucu CAGG'den
  okur (`aralik=saat` doğrudan, `aralik=gun` CAGG üstünde günlük toplar). **materialized_only
  = false** → real-time aggregation: henüz materialize edilmemiş son veri de görünür; testte
  manuel refresh gerekmez.
- **RBAC.** `enerji:yaz` izni katalog eklenir (`kalite:oku/yaz`, `enerji:oku` katalogda zaten
  vardı); görev rolleri `kalite` (kalite:oku/yaz) ve `enerji` (enerji:oku/yaz).

## Sonuçlar
- (+) CAPA yaşam döngüsü, geçersiz geçiş 409, `kalite:yaz` 403, tenant izolasyonu, enerji trend
  toplulaştırması ve migration fan-out + CAGG up/down entegrasyon testli ve kalıcı.
- (+) Enerji trendi hızlı okunur; ADR-0006'nın ertelediği CAGG işi kapanır.
- (+) OEE / üretim hattı (S3/S6/S7) S10'dan **etkilenmez**; kalite/enerji ayrık modüllerdir.
- (−) CAGG migration `autocommit_block` gerektirir; test DB **TSL** TimescaleDB imajı ister
  (`add_continuous_aggregate_policy` community imajda yok). Fan-out testinde erken doğrulanır.
- (−) `kaldi` denetim otomatik uygunsuzluk açmaz (elle bağ) — otomatik köprü YAGNI kapsamında
  ertelendi.

## Notlar
- Migration `b7e4c2f9a016` (down `a3d9f1c52e84`); `public` + ≥2 tenant şemasında fan-out
  up/down testli (`test_s10_migration.py`); hypertable + CAGG dahil.
- Miktar/tüketim `Numeric(18,3)` (Decimal aritmetik); istek DTO alanları `Decimal`, cevap DTO
  alanları `float` (outbox/realtime `govde` JSON-native olmalı → `float(...)`).
- Ertelenen: compression/retention politikaları (S19); kalite→OEE kalite oranı beslemesi;
  edge enerji ingestion (Faz 5).
