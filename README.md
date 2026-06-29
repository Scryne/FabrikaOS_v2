# FabrikaOS

Çok kiracılı (multi-tenant) **MES + ERP hibrit** endüstriyel yönetim platformu (B2B SaaS).
Türkiye'deki orta/büyük ölçekli metal sanayi tesisleri için; KVKK uyumlu, modül modül
lisanslanabilir.

> Bu depo, `FabrikaOS_Proje_Plani.pdf` şartnamesinin faz-faz uygulamasıdır. Geliştirme planı:
> `~/.claude/plans/...buzzing-cake.md` (faz/sprint kırılımı, kabul kriterleri, DoD).

## Mimari (özet)

- **Modüler Monolit** · Python 3.12 / FastAPI (async)
- **Çok kiracılılık:** şema-başına-tenant — `public` (control-plane) + `tenant_<slug>` (her fabrika)
- **Tenant çözümleme:** subdomain (`fabrika-a.fabrikaos.com`) veya `X-Tenant` header → `search_path`
- **Veri:** PostgreSQL 16 + TimescaleDB · Redis · MinIO (S3)
- **Saha:** MQTT + Edge Gateway (OPC-UA/Modbus)
- **Frontend:** React + TypeScript + Vite + Ant Design

## Dizin yapısı

```
backend/app/        # FastAPI uygulaması
  core/             # çekirdek (config, logging, exceptions, responses, middleware)
    db/             # base/metadata, session, tenancy (search_path), fanout, audit
    security/       # parola (argon2id), jwt, rbac (deps), ratelimit, token deposu
  api/              # /api/v1 router toplayıcı (S1: saglik)
  control_plane/    # public şema: Tenant, Abonelik + provizyonlama (S2)
  kimlik/           # tenant kimlik & RBAC: Kullanici/Rol/Izin + /kimlik, /kullanicilar (S2)
  modules/          # tenant iş modülleri (S3+)
backend/migrations/ # Alembic iki ağaç: public/ + tenant/ (fan-out)
backend/tests/      # birim + entegrasyon testleri
docs/adr/           # mimari karar kayıtları
docker-compose.yml  # api, db, redis, minio, mqtt, traefik
```

## Geliştirme ortamı

### Gereksinimler
- **Docker Desktop** (zorunlu — tüm yığını çalıştırmak için)
- (Opsiyonel) Python 3.12 — yerel hızlı test/lint için

### Çalıştırma (Docker)
```bash
cp .env.example .env
docker compose up --build
```
- API: http://localhost:8000
- Sağlık: http://localhost:8000/saglik
- Swagger/OpenAPI: http://localhost:8000/docs
- Traefik panosu (dev): http://localhost:8080

### Yerel test/lint (Python kuruluysa)
Entegrasyon testleri çalışan bir PostgreSQL ister (`fabrikaos_test` veritabanını otomatik
oluşturur). Önce altyapıyı kaldır:
```bash
docker compose up -d db redis
pip install -e ".[dev]"
ruff check backend && ruff format --check backend
mypy
pytest                       # TEST_DATABASE_URL ile override edilebilir (CI)
```

### Docker içinde test
```bash
docker compose run --rm api pytest
```

## Veritabanı, migrasyon ve provizyonlama (S2)

Çok kiracılılık **şema-başına-tenant**'tır: control-plane `public`, her fabrika `tenant_<slug>`.
Migrasyonlar iki Alembic ağacında tutulur ve **fan-out** edilir (bkz. `docs/adr/0004-*`).

```bash
# Control-plane (public) şemasını yükselt
python -m alembic --name public upgrade head

# Tüm aktif tenant şemalarına fan-out
python -m alembic --name tenant upgrade head

# Yeni tenant provizyonla (public kayıt + şema + migrate + seed; idempotent)
python -c "import asyncio; from app.control_plane.provizyon import tenant_provizyonla; \
asyncio.run(tenant_provizyonla(slug='fabrika-a', ad='Fabrika A', \
admin_eposta='admin@fabrika-a.test', admin_parola='Parola123!'))"
```

Tenant'a istek atarken `X-Tenant: <slug>` başlığı (veya `<slug>.fabrikaos.localhost` subdomain)
kullanılır. Kimlik: `POST /api/v1/kimlik/token` (OAuth2 şifre akışı) → `Authorization: Bearer`.

## Konvansiyonlar
- **Identifier:** Türkçe-ASCII (ç/ş/ı/ğ/ö/ü yok) — bkz. `docs/veri-sozlugu.md`
- **API:** `/api/v1`, kaynak-odaklı çoğul Türkçe uçlar, yanıt zarfı `{success,message,data,meta}`
- **Commit:** Conventional Commits · **Dallanma:** trunk-based · **Sürüm:** SemVer
- **Mimari kararlar:** `docs/adr/NNNN-*.md`

## Yol haritası (fazlar)
Faz 0 Temel → Faz 1 MVP → Faz 2 Saha & Modüller → Faz 3 Zekâ → Faz 4 Lisanslama → Faz 5 Operasyon & GA.
Detay için geliştirme planına bakınız.
