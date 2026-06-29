# ADR-0006: Zaman serisi — TimescaleDB hypertable + OEE

Durum: Kabul
Tarih: 2026-06-29

## Bağlam
Üretim verisi (`uretim_verileri`) yüksek hacimli, zaman-eksenli bir akıştır; klasik tablo
ve indeksler zamanla yavaşlar. OEE (Kullanılabilirlik × Performans × Kalite) bu veriden
makine ve zaman aralığı bazında toplulaştırılır.

## Karar
- **`uretim_verileri` bir TimescaleDB hypertable'dır** (partition kolonu `zaman`).
  Hypertable kuralı gereği birincil anahtar partition kolonunu içerir → `(zaman, id)`;
  `id` bir `Identity` (server-generated) sütundur.
- **`create_hypertable` adımı migration içindedir** ve [ADR-0004](0004-alembic-fan-out.md)
  fan-out döngüsünde HER tenant şemasında çalışır (`search_path` ayarlı; tablo adı şema
  öneki taşımaz). Idempotent (`if_not_exists => TRUE`).
- **OEE saf bir fonksiyondur** (`modules/uretim/oee.py`): DB/IO yok, deterministik →
  kapsamlı birim testlerle güvencelenir. Aralık/çoklu-kayıt OEE'si servis katmanında
  toplulaştırılır; toplam ideal süreden "efektif çevrim süresi" türetilerek **aynı saf
  fonksiyon** yeniden kullanılır (tek doğruluk kaynağı).
- Sorgu için `(makine_id, zaman)` bileşik indeksi.

## Sonuçlar
- (+) Zaman-aralığı sorguları ve gelecekteki chunk/compression/retention için doğal zemin.
- (+) OEE mantığı saf ve testli; aggregation onu yeniden kullanır, kopya formül yok.
- (+) Hypertable adımı fan-out + provizyonlama ile her tenant'a tutarlı uygulanır (testli).
- (−) Bileşik PK `(zaman, id)`; tekil `id` ile erişim PK'yi kullanmaz (indeksle çözülür).
- (−) **Continuous aggregate** (vardiya/gün özet), compression ve retention politikaları
  bu sprintte ELE ALINMADI: continuous aggregate `CREATE MATERIALIZED VIEW ... WITH
  (timescaledb.continuous)` işlem bloğu dışında çalışmalı (Alembic `autocommit_block`
  gerekir). Performans optimizasyonu olarak ileride (S10/S19) bilinçli eklenecek; şimdilik
  `/oee/ozet` anlık toplulaştırma + indeks ile karşılanır.
