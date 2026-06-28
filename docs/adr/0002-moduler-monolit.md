# ADR-0002: Mimari stil — Modüler Monolit

Durum: Kabul
Tarih: 2026-06-29

## Bağlam
27 modüllü bir MES+ERP platformu; küçük ekip, hızlı teslimat ve düşük operasyon yükü
hedefleniyor. Mikroservis mimarisi bu aşamada gereksiz dağıtık sistem karmaşıklığı getirir.

## Karar
**Modüler Monolit**: tek dağıtım birimi, içte net modül sınırları
(`modules/<ad>/` → router/service/repository/models/schemas/tasks/events) ve paylaşılan
çekirdek (`core/`). CPU-yoğun/zamanlanmış işler Celery worker'lara devredilir.

## Sonuçlar
- (+) Tek repo/tek deploy; basit operasyon, kolay yerel geliştirme.
- (+) Net modül sınırları ileride servis ayrıştırmaya (gerekirse) zemin hazırlar.
- (−) Modüller arası bağımlılık disiplini koddan zorlanmalı (review + ADR).
