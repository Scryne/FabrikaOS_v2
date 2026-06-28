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
  core/             # çekirdek (config, logging, exceptions, responses, middleware, db, security)
  api/              # /api/v1 router'ları (S1: saglik)
  control_plane/    # public şema (S2+)
  modules/          # tenant modülleri (S3+)
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
```bash
pip install -e ".[dev]"
ruff check backend
mypy
pytest
```

### Docker içinde test
```bash
docker compose run --rm api pytest
```

## Konvansiyonlar
- **Identifier:** Türkçe-ASCII (ç/ş/ı/ğ/ö/ü yok) — bkz. `docs/veri-sozlugu.md`
- **API:** `/api/v1`, kaynak-odaklı çoğul Türkçe uçlar, yanıt zarfı `{success,message,data,meta}`
- **Commit:** Conventional Commits · **Dallanma:** trunk-based · **Sürüm:** SemVer
- **Mimari kararlar:** `docs/adr/NNNN-*.md`

## Yol haritası (fazlar)
Faz 0 Temel → Faz 1 MVP → Faz 2 Saha & Modüller → Faz 3 Zekâ → Faz 4 Lisanslama → Faz 5 Operasyon & GA.
Detay için geliştirme planına bakınız.
