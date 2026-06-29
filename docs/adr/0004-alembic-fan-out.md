# ADR-0004: Migrasyon stratejisi — Alembic çok-şemalı fan-out

Durum: Kabul
Tarih: 2026-06-29

## Bağlam
[ADR-0003](0003-sema-basina-tenant.md) gereği şema-başına-tenant kullanıyoruz. Bir model
değişikliği yalnızca tek şemaya değil, **`public` + tüm aktif `tenant_<slug>` şemalarına**
uygulanmalıdır. Standart tek-şema Alembic kurulumu bu ihtiyacı karşılamaz.

## Karar
**İki ayrı Alembic ağacı + fan-out runner.**
- `backend/migrations/public/` → control-plane tabloları (PublicBase metadata). Bir kez uygulanır.
- `backend/migrations/tenant/` → iş modülü tabloları (TenantBase metadata, şemasız). Hedef
  şema(lar)a uygulanır.
- `tenant/env.py` fan-out döngüsü: hedef şemalar `config.attributes['schemas']` (programatik),
  `-x schema=...` (CLI/autogenerate) ya da `public.tenant`'taki tüm aktif tenant'lardan gelir.
  Her şema kendi `alembic_version` tablosunu tutar (`version_table_schema`).
- `core/db/fanout.py` programatik API: `public_yukselt`, `tenant_yukselt_tek/tum`, `*_indir`.
  Senkrondur; async bağlamdan `asyncio.to_thread` ile çağrılır.
- `naming_convention` zorunlu (`ix_/fk_/uq_/ck_/pk_`) → fan-out ve şema karşılaştırması öngörülebilir.
- Async migration (asyncpg, tek sürücü); `run_sync` sonrası açık `commit` (aksi halde DDL geri alınır).

Yeni tenant provizyonlama (`control_plane/provizyon.py`) aynı runner'ı tek şema için çağırır:
`public kayıt → CREATE SCHEMA → tenant migrate (fan-out tek) → seed`. İdempotenttir.

## Sonuçlar
- (+) Tek revision tüm tenant'lara tutarlı uygulanır; provizyonlama ile aynı kodu paylaşır.
- (+) `upgrade()` + `downgrade()` her ikisi de zorunlu ve testli (geri alınabilirlik).
- (+) DoD: `public` + en az iki tenant şemasında temiz uygulama + downgrade testle kanıtlı.
- (−) İki ağaç bakım yükü getirir; autogenerate için tenant tarafında `tenant_sablon` şablon
  şeması gerekir.
- (−) Çok sayıda tenant'ta fan-out süresi artar → ileride paralel/batch uygulama düşünülebilir.
