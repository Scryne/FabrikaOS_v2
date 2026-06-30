# FabrikaOS

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20TimescaleDB-336791?logo=postgresql&logoColor=white)

Çok kiracılı (multi-tenant) **MES + ERP hibrit** endüstriyel yönetim platformu (B2B SaaS).
Türkiye'deki orta/büyük ölçekli metal sanayi tesisleri için; KVKK uyumlu, **modül modül
lisanslanabilir**. Operatör bir olayı saniyeler içinde görüp aksiyona dönüştürür; yönetici
dağınık tablolar yerine tek panodan tesisi yönetir.

> Bu depo, `FabrikaOS_Proje_Plani.pdf` şartnamesinin **faz-faz** uygulamasıdır.
> Tam yol haritası (6 faz / 22 sprint, kabul kriterleri + DoD): **[`docs/yol-haritasi.md`](docs/yol-haritasi.md)**.

## Durum

**Faz 0 (Temel) ✅ · Faz 1 (MVP) ✅ — gösterilebilir, canlı, izole ürün hazır. Faz 2 başladı (S8 ✅).**

| Sprint | Konu | Durum |
|---|---|---|
| S1–S2 | Çekirdek + çok kiracılılık + kimlik/RBAC | ✅ |
| S3–S4 | Üretim/OEE + İş emri/Bakım (backend) | ✅ |
| S5 | SPA iskeleti + Auth (frontend) | ✅ |
| S6 | Üretim/İş emri ekranları + ECharts pano + sunucu-taraflı tablo | ✅ |
| S7 | Gerçek zaman (WebSocket + Redis pub/sub) + uçtan uca + izolasyon | ✅ |
| S8 | Edge & Ingestion (MQTT + store-and-forward + cihaz yönetimi) | ✅ |
| S9 → S22 | Stok/satınalma, kalite, modüller, AI, lisanslama, GA | ⬜ planlı |

Backend: **76 test** (tenant izolasyonu + RBAC + fan-out + OEE + iş emri yaşam döngüsü +
gerçek-zaman). Frontend: **57 test** (Vitest + RTL) + Playwright **E2E** (canlı güncelleme);
`tsc --strict` + ESLint temiz. Ayrıntı: [yol haritası](docs/yol-haritasi.md).

## Mimari (özet)

- **Modüler Monolit** · Python 3.12 / FastAPI (async) · SQLAlchemy 2.0 + Alembic
- **Çok kiracılılık:** şema-başına-tenant — `public` (control-plane) + `tenant_<slug>` (her fabrika)
- **Tenant çözümleme:** subdomain (`fabrika-a.fabrikaos.com`) veya `X-Tenant` header → `search_path`
- **Veri:** PostgreSQL 16 + TimescaleDB (hypertable) · Redis · MinIO (S3 uyumlu)
- **Gerçek zaman:** FastAPI WebSocket + Redis pub/sub, tenant-kapsamlı kanallar (`tenant:<slug>:olaylar`) — canlı OEE/durum/iş emri
- **Saha:** MQTT + Edge Gateway (OPC-UA/Modbus) — *Faz 2*
- **Frontend:** React 18 + TypeScript (strict) + Vite + Ant Design v5 (özel koyu tema) + ECharts + TanStack Query
- **Kimlik:** OAuth2/JWT + RBAC, argon2id, rotasyonlu refresh (Redis iptal listesi)

## Dizin yapısı

```
backend/app/        # FastAPI uygulaması
  core/             # çekirdek (config, logging, exceptions, responses, middleware, olaylar, gercekzaman, sorgu)
    db/             # base/metadata, session, tenancy (search_path), fanout
    security/       # parola (argon2id), jwt, rbac (deps), ratelimit, token deposu, redis
  api/              # /api/v1 router toplayıcı + ws (gerçek-zaman WebSocket)
  control_plane/    # public şema: Tenant, Abonelik + provizyonlama
  kimlik/           # tenant kimlik & RBAC: Kullanici/Rol/Izin + /kimlik, /kullanicilar
  modules/          # tenant iş modülleri: uretim/, isemri/, bakim/ (S3+)
backend/migrations/ # Alembic iki ağaç: public/ + tenant/ (fan-out)
backend/tests/      # birim + entegrasyon testleri
frontend/src/       # api, components, layouts, modules, store, i18n, tema, routes
frontend/e2e/       # Playwright E2E (gerçek-zaman canlı güncelleme)
docs/adr/           # mimari karar kayıtları (0001–0009)
docs/yol-haritasi.md# faz/sprint planı
docker-compose.yml  # api, db, redis, minio, mqtt, traefik
```

## Geliştirme ortamı

### Gereksinimler
- **Docker Desktop** (backend yığını için zorunlu)
- **Node.js 20+** (frontend için)
- (Opsiyonel) Python 3.12 — yerel hızlı test/lint için

### Backend (Docker)
```bash
cp .env.example .env
docker compose up --build
```
- API: http://localhost:8000
- Sağlık: http://localhost:8000/saglik
- Swagger/OpenAPI: http://localhost:8000/docs
- Traefik panosu (dev): http://localhost:8080

### Frontend
```bash
cd frontend
cp .env.example .env        # API taban adresi vb.
npm install
npm run dev                 # http://localhost:5173
```
- Giriş: `/giris` · Uygulama: korunan rotalar (RBAC'a göre menü)
- Tasarım önizleme (yalnız DEV, backend gerektirmez): `/onizleme` — KPI / OEE / pano
- Görsel sistem: **nötr antrasit koyu tema, mavi yalnızca vurgu** (bkz. [`DESIGN.md`](DESIGN.md))

Frontend kalite:
```bash
npm run lint && npm run typecheck && npm test
npm run test:e2e            # Playwright E2E — çalışan yığın + seed'li tenant ister (E2E_BASE/E2E_API ile origin)
```

### Backend test/lint (Python kuruluysa)
Entegrasyon testleri çalışan bir PostgreSQL ister (`fabrikaos_test` veritabanını otomatik oluşturur):
```bash
docker compose up -d db redis
pip install -e ".[dev]"
ruff check backend && ruff format --check backend
mypy
pytest                       # TEST_DATABASE_URL ile override edilebilir (CI)
```
Docker içinde: `docker compose run --rm api pytest`

## Veritabanı, migrasyon ve provizyonlama

Çok kiracılılık **şema-başına-tenant**'tır: control-plane `public`, her fabrika `tenant_<slug>`.
Migrasyonlar iki Alembic ağacında tutulur ve **fan-out** edilir (bkz. [`docs/adr/0004-*`](docs/adr/0004-alembic-fan-out.md)).

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

## Saha & Ingestion (S8)

Sahadan otomatik veri akışı (bkz. [`docs/adr/0010-*`](docs/adr/0010-edge-ingestion-mqtt.md)).
`docker compose up -d db redis mqtt` sonrası:

```bash
# Bulut Ingestion Worker (MQTT abonesi → tenant şemasına idempotent yazım)
MQTT_HOST=localhost python -m app.ingestion.worker

# Edge Gateway Agent (simülatör PLC → store-and-forward → MQTT)
EDGE_BROKER_HOST=localhost EDGE_TENANT_SLUG=<slug> EDGE_CIHAZ_KOD=GW-1 \
  python -m edge.agent
```

Cihaz önce kaydedilir (`POST /api/v1/saha/cihazlar`, `saha:yaz`) ve `makine_kod`'lar `makineler`'de
var olmalıdır. Ölçümler `uretim_verileri`'ne yazılır → OEE panosu elle giriş olmadan güncellenir.
REST/CSV ile de gönderilebilir: `POST /api/v1/saha/olcumler` (+`/csv`, `edge` izni).

## Konvansiyonlar
- **Identifier:** Türkçe-ASCII (ç/ş/ı/ğ/ö/ü yok) — bkz. [`docs/veri-sozlugu.md`](docs/veri-sozlugu.md)
- **API:** `/api/v1`, kaynak-odaklı çoğul Türkçe uçlar, yanıt zarfı `{success, message, data, meta}`
- **Commit:** Conventional Commits · **Dallanma:** trunk-based · **Sürüm:** SemVer
- **Mimari kararlar:** [`docs/adr/NNNN-*.md`](docs/adr/) (0001–0010 mevcut)

## Yol haritası

**Faz 0** Temel → **Faz 1** MVP → **Faz 2** Saha & Modüller → **Faz 3** Zekâ →
**Faz 4** Lisanslama & Dış Entegrasyon → **Faz 5** Operasyon & GA (`v1.0.0`).

Sprint-sprint kapsam, kabul kriterleri, DoD ve geçiş kapıları: **[`docs/yol-haritasi.md`](docs/yol-haritasi.md)**.
