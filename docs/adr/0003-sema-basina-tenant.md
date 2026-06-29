# ADR-0003: Çok kiracılılık — Şema-başına-tenant + search_path

Durum: Kabul
Tarih: 2026-06-29

## Bağlam
FabrikaOS çok kiracılı bir SaaS'tır; bir fabrikanın verisi başka bir fabrikaya **asla**
sızmamalıdır (R3 riski — en pahalı hata). İzolasyon için üç ana seçenek var:
1. Tek şema + her tabloda `tenant_id` filtresi (uygulama disiplinine bağımlı, sızıntıya açık).
2. **Şema-başına-tenant** (`tenant_<slug>`) — her fabrika kendi PostgreSQL şemasında.
3. Veritabanı-başına-tenant (operasyonel olarak ağır, çok sayıda tenant'ta ölçeklenmez).

PostgreSQL Row-Level Security (RLS) bilinçli olarak kapsam dışıdır (PDF: "Won't now").

## Karar
**Şema-başına-tenant.** Control-plane tabloları (`tenant`, `abonelik`, ...) `public`
şemasında; her tenant'ın iş verisi izole bir `tenant_<slug>` şemasında tutulur.

İzolasyon **tek noktada** `search_path` ile sağlanır (`core/db/tenancy.py`):
- İstek başına oturumda `select set_config('search_path', 'tenant_<slug>, public', true)`
  çağrılır. Üçüncü argüman `true` (is_local) → ayar **işleme özeldir**; commit/rollback'te
  otomatik sıfırlanır, böylece bağlantı havuza dönerken sızmaz.
- Tenant tabloları sabit şema öneki **kullanmaz** (`tenant_xyz.tablo` yasak); `search_path`'e
  güvenir. Control-plane modelleri ise `schema="public"` ile her zaman public'e bağlanır.
- Slug, DNS-label biçiminde katı doğrulanır (`^[a-z0-9-]+$`); şema adı güvenilmez girdiden
  string birleştirmeyle üretilmez.

JWT'deki `tenant_slug` claim'i isteğin subdomain'i ile eşleşmek zorundadır (cross-tenant 403).

## Sonuçlar
- (+) Güçlü izolasyon: yanlış tenant'ın tablosuna erişim fiziksel olarak ayrı şemadadır.
- (+) Tenant-bazlı yedekleme/geri yükleme ve KVKK ihraç/silme şema bazında yapılabilir (S20).
- (+) Tek savunma hattı tek dosyada → denetlenebilir; zorunlu izolasyon testiyle güvencelenir.
- (−) `search_path` disiplini kritik: yanlış uygulama = sızıntı. Bu yüzden CI'da kalıcı
  izolasyon testi (A token'ı B verisine erişemez) zorunludur.
- (−) Migrasyonlar tüm şemalara uygulanmalı → fan-out gerekir (bkz. [ADR-0004](0004-alembic-fan-out.md)).
