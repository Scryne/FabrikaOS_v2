# S8 — Edge & Ingestion · Tasarım (Spec)

> Faz 2 / Sprint S8. Onaylı yol haritası: `docs/yol-haritasi.md` ve `~/.claude/plans/…buzzing-cake.md` §4 (FAZ 2 / S8).
> Bağlayıcı skill'ler: `tenant-rbac-conventions`, `turkce-identifier-standardi`, `alembic-fan-out`.

## 1. Amaç ve Kabul Kriterleri

Sahadan **otomatik** veri akışını kurmak: simüle PLC verisi `Edge → MQTT → Ingestion → uretim_verileri → OEE panosu`'na **elle giriş olmadan** akar; ingestion **tenant-aware**; bağlantı koptuğunda **store-and-forward kayıpsız**.

Kabul kriterleri (plandan):
1. Simüle PLC verisi MQTT→ingestion→OEE panosuna elle giriş olmadan akar.
2. Ingestion tenant-aware (doğru tenant şemasına yazar, çapraz-tenant sızıntı yok).
3. Bağlantı kopunca store-and-forward **kayıpsız** (replay'de çift-sayma yok).
4. Ek DoD: Edge için kontrat/şema doğrulama; **ADR-0010** (Edge & Ingestion).

## 2. Kapsam Kararları (onaylı)

| Karar | Seçim | Gerekçe |
|---|---|---|
| Saha katmanı | **Simülatör + pluggable sürücü arayüzü** | Kabul kriteri "simüle PLC" der; donanım bağımlılığı yok, %100 test edilebilir. OPC-UA/Modbus = belgelenmiş adaptör iskeleti (seam); gerçek sürücü + mTLS **Faz 5 sertleştirmeye ertelenir** (ADR-0010). |
| Veri şekli | **Edge aralık özeti → `uretim_verileri`** | Edge, PLC sayacı/durumunu yerel özetler ve mevcut `UretimVerisi` şeklinde yayınlar → OEE hattı (S3/S6/S7) yeniden kullanılır, anında çalışır. Yeni ham hypertable yok (S10/S19 işi). |
| Ingestion runtime | **Ayrı worker süreci (aiomqtt)** | Plan'daki "Bulut Ingestion Worker"; API yaşam döngüsünden bağımsız ölçeklenir. Saf işleme fonksiyonu broker'sız test edilir. |
| Frontend | **Minimal salt-okunur Cihazlar ekranı** | Saha katmanını görünür/demolanabilir yapar; cihaz CRUD/CSV-UI sonraki sprinte bırakılır (YAGNI). |

### 2.1 İyileştirmeler (bu tasarımda katılan)
- **Cihaz = gateway** (tek makineye FK ile bağlı *değil*); ölçüm `makine_kod` taşır → bir gateway **N makine** köprüleyebilir (gerçekçi + model daha basit).
- **REST `/saha/olcumler` toplu (batch)** kabul eder; CSV içe-aktarma aynı toplu yazma yolunu kullanır → kesinti sonrası replay ve içe-aktarma verimli, kısmi hata net raporlanır.
- Ingestion mesaj başına `tenant_slug_ctx` ContextVar'ını set eder → **JSON log korelasyonu** (§3.7: `tenant`+`request_id`).
- Edge ajanı **graceful shutdown** (SIGTERM → tamponu flush) + reconnect **backoff**.
- Frontend `uretim.eklendi` olayında Cihazlar sorgusunu invalidate eder → **`son_gorulme` canlı** (akışın görsel kanıtı).

## 3. Bileşenler ve Topoloji

```
edge/                          # YENİ — on-prem Edge Gateway Agent (app paketini import ETMEZ)
backend/app/ingestion/         # YENİ — bulut Ingestion Worker (app paketini paylaşır)
backend/app/modules/saha/      # YENİ — cihaz yönetimi + REST/CSV ingestion (standart modül)
backend/migrations/tenant/…    # YENİ — saha_cihazlar + saha_alinan_olcum (fan-out)
frontend/src/modules/saha/     # YENİ — salt-okunur Cihazlar listesi
```

### 3.1 `edge/` — Edge Gateway Agent (bağımsız paket)
`app`'i import etmez; on-prem deploy edilir. Kendi minimal bağımlılığı (`aiomqtt`, `pydantic`, stdlib `sqlite3`).

- `edge/ayar.py` — `EdgeAyar` (env/`edge.yaml`): broker URL, `tenant_slug`, `cihaz_kod`, sürücü tipi, poll/özet aralığı, köprülenen makine listesi (`makine_kod` → sürücü kanalı).
- `edge/suruculer/__init__.py` — `SahaSurucu` arayüzü (Protocol): `oku() -> list[HamOkuma]` (ham sinyal: `makine_kod`, sayaç, durum, zaman).
- `edge/suruculer/simulasyon.py` — `SimulasyonSurucu`: deterministik PLC (monoton artan sayaç + aralıklı arıza/yavaşlama; tohumlu rastgelelik → testlerde sabit).
- `edge/suruculer/opcua.py`, `edge/suruculer/modbus.py` — **belgelenmiş adaptör iskeleti**: net "nasıl uygulanır" docstring + `NotImplementedError`. Seam burada; gerçek implementasyon Faz 5.
- `edge/ozetleyici.py` — **saf** agregatör: aralık içi ham okumaları (sayaç deltası + durum süreleri) `OlcumPaketi`'ne çevirir (`UretimVerisi` şekli + `olcum_id: uuid4` + `vardiya`).
- `edge/tampon.py` — **store-and-forward**: dayanıklı yerel kuyruk (stdlib `sqlite3`, tek dosya). `ekle(paket)`, `bekleyenler() -> list`, `onayla(olcum_id)`. Süreç yeniden başlasa dosyadan kurtulur.
- `edge/yayinci.py` — `aiomqtt` publisher: `fabrikaos/<tenant_slug>/<cihaz_kod>/olcum` topic'ine **QoS 1**; tamponu okur → yayınlar → PUBACK'te `onayla`. Broker yoksa tampon dolu kalır, reconnect'te replay.
- `edge/agent.py` — `python -m edge.agent`: döngü `oku → özetle → tampona ekle → (bağlıysa) yayınla`; SIGINT/SIGTERM'de temiz kapanış.

### 3.2 `backend/app/ingestion/` — Ingestion Worker (`app` paylaşır)
- `isleyici.py` — **saf** `mesaj_coz(topic: str, payload: bytes) -> tuple[str, OlcumPaketi]`: topic'ten `tenant_slug`+`cihaz_kod` ayıkla, payload'ı Pydantic ile doğrula. Broker'sız test edilir.
- `service.py` —
  - `olcum_yaz_toplu(slug, cihaz_kod, paketler) -> IngestSonuc(yazilan, atlanan, hatali)`: **tek** tenant oturumu açar (`search_path = tenant_<slug>`); cihaz registry doğrular (kayıtlı+aktif); her paket için `makine_kod`→`makineler` çözer (tenant içi, yoksa `hatali`); **idempotency** (`saha_alinan_olcum` `ON CONFLICT DO NOTHING`; çakışma → `atlanan`); `UretimVerisi` yazar; `cihaz.son_gorulme` günceller; commit; sonra **makine başına tekilleştirilmiş** `uretim.eklendi` realtime olayı yayınlar (`yayinla`).
  - Tek-paket yazma = 1 elemanlı toplu.
- `worker.py` — `python -m app.ingestion.worker`: `aiomqtt` ile `fabrikaos/+/+/olcum`'a abone; her mesaj → `mesaj_coz` → `olcum_yaz_toplu`; her mesaj için `tenant_slug_ctx`/`request_id_ctx` set + hata **izole** (loop çökmez). Yeni `ingestion` compose servisi.

### 3.3 `backend/app/modules/saha/` — Cihaz Yönetimi + REST/CSV Ingestion (standart modül)
- `models.py` — `Cihaz` (`saha_cihazlar`) + `AlinanOlcum` (`saha_alinan_olcum`).
- `schemas.py` — `OlcumPaketi` (paylaşılan kontrat; edge + ingestion + REST aynı şemayı kullanır), `CihazCevapDTO`, `CihazOlusturDTO`, `OlcumKabulDTO`.
- `repository.py`, `service.py` (ingestion `service`'i yeniden kullanır), `router.py`:
  - `GET /saha/cihazlar` → `saha:oku` (sayfalama/arama/sıralama, `SunucuTablo` uyumlu).
  - `POST /saha/cihazlar` → `saha:yaz` (+ audit).
  - `GET /saha/cihazlar/{id}` → `saha:oku`.
  - `POST /saha/olcumler` → `izin_gerekli("edge")`; gövde = `OlcumPaketi` **listesi** (toplu); `olcum_yaz_toplu`'ya gider; `IngestSonuc` döner; idempotent.
  - `POST /saha/olcumler/csv` → `izin_gerekli("edge")`; multipart CSV → satır→`OlcumPaketi` → aynı toplu yol.

## 4. Veri Modeli ve Migration (alembic-fan-out)

Tenant ağacına yeni revizyon (`down_revision` = mevcut tenant head; uygulama anında `alembic heads` ile doğrulanır). Hypertable **yok**.

- **`saha_cihazlar`** (`Cihaz`): `id` (Identity PK), `kod` (String, **unique**, index), `ad`, `protokol` (`simulasyon|opcua|modbus`), `aktif` (bool, default True), `son_gorulme` (timestamptz, nullable), `ZamanDamgaliMixin`. *Makineye sabit FK yok* (gateway N makine köprüler).
- **`saha_alinan_olcum`** (`AlinanOlcum`, idempotency): `olcum_id` (UUID **PK**), `makine_id` (BigInt), `alinma_zamani` (timestamptz). Replay çift-saymayı `ON CONFLICT DO NOTHING` ile önler. (Hypertable'ın unique-partition kısıtı yüzünden ayrı normal tablo; `uretim_verileri` PK'sine dokunulmaz.)
  - *Not (gelecek):* bu tablo sınırsız büyür → retention/temizleme S19/S20'de ele alınır (şimdilik kapsam dışı, YAGNI).

**Fan-out DoD:** `public` + ≥2 tenant şemasında up/down testli; downgrade tabloları düşürür.

**Seed (`kimlik/izinler.py`):** `IZIN_KATALOGU`'na eklenir — `saha:oku`, `saha:yaz`, `edge`. `admin` rolü hepsini alır (katalog tamamı); `izleyici` `saha:oku` alır (`:oku` kuralı). `edge` için yeni varsayılan rol: `VARSAYILAN_ROLLER["saha-cihaz"] = {"edge"}` (servis/cihaz hesapları). REST ingestion testi `edge` izinli kullanıcı oluşturur.

## 5. Veri Akışı (uçtan uca)

1. Sürücü `oku()` → ham sinyal (her poll, örn. 5 sn).
2. Agregatör aralık boyunca toplar (örn. 60 sn) → `OlcumPaketi` (`olcum_id`, `makine_kod`, `vardiya`, OEE girdileri).
3. Paket **tampona** yazılır → MQTT'ye yayınlanır (QoS1). PUBACK → tampon onayı. Broker yoksa tamponda kalır → reconnect'te replay (**kayıpsız**, `olcum_id` ile çift yok).
4. Ingestion: mesaj → `mesaj_coz` → `olcum_yaz_toplu`: tenant oturumu, registry+makine doğrulama, idempotency, `UretimVerisi` yaz + `son_gorulme` + commit → makine-bazlı `uretim.eklendi`.
5. OEE özeti/pano zaten `uretim_verileri` okur → **elle giriş olmadan canlı güncellenir** (S6/S7 hattı) ✅.

**Tenant farkındalığı & dev "auth":** topic `fabrikaos/<slug>/<cihaz>/olcum`. Ingestion slug'ı topic'ten alır, tenant aktif mi + cihaz kayıtlı/aktif + makine eşlemesi doğrular; bilinmeyen → **düşür + logla** (yazma yok). Dev'de mosquitto anonim → registry doğrulama tek kapı; MQTT-seviyesi mTLS/credential **Faz 5'e ertelenir (ADR-0010)**.

## 6. Hata Yönetimi

- **Edge:** broker erişilemez → tampon + üstel backoff retry; sürücü hatası → logla, döngüyü öldürme; bozuk config → fail-fast başlangıçta; SIGTERM → tamponu flush + temiz çıkış.
- **Ingestion:** bozuk payload / bilinmeyen tenant·cihaz·makine → logla + düşür (loop ayakta); tekrar `olcum_id` → sessiz atla; DB hatası → logla + devam (uçtan uca at-least-once: edge tampon + idempotency).
- **REST:** doğrulama → 422; bilinmeyen cihaz/makine → ilgili satır `hatali` (toplu sonuç) / tekil 404; `edge` izni yok → 403; tekrar `olcum_id` → 200, satır `atlanan` (çift yazma yok).

## 7. Test Stratejisi (DoD + 7 kritik aile)

**Her zaman koşan (broker'sız, deterministik):**
- *Edge birim:* simülatör determinizmi (tohumlu); agregatör (sayaç deltası→paket, vardiya); tampon store-and-forward (ekle→bekleyen→onay→silinir; dosyadan "yeniden başlat"ta kurtulur; broker-down→replay **kayıpsız + `olcum_id` çift yok**); `OlcumPaketi` şema doğrulama (kontrat).
- *Ingestion birim:* `mesaj_coz` (iyi/bozuk payload, topic→slug/cihaz); `olcum_yaz_toplu` idempotency (2. yazım `atlanan`); bilinmeyen cihaz/makine → yazma yok; **tenant izolasyonu** — `alfa` mesajı `beta` şemasına yazılmaz (servis doğrudan çağrılır, kritik aile).
- *REST entegrasyon (mevcut TestClient hattı):* `/saha/cihazlar` CRUD (RBAC `saha:oku/yaz`, tenant izolasyonu, 403/404/422, audit); `/saha/olcumler` (`edge` izni; **OEE'ye akış** — yazımdan sonra `GET /oee/ozet` veriyi yansıtır; idempotency; izolasyon); `/saha/olcumler/csv` (parse + yaz + kısmi hata).

**MQTT round-trip (gerçek broker, koşullu):**
- `testcontainers` ile mosquitto (anonim config) kaldır → edge'in yayınladığı paket worker tarafından doğru tenant şemasına yazılır (uçtan uca). Docker yoksa **`pytest.mark.skip`** (DoD'u broker'sız testler zaten karşılar).

**Sözleşme/CI:** `openapi.json` regen + frontend `npm run codegen`. CI `backend` job'ına gerçek-broker testi `testcontainers` ile koşar (ubuntu runner'da Docker mevcut); kırılganlık olursa skip. `ruff`+`mypy` temiz; FE `eslint`+`tsc`+`vitest`+`build` temiz.

**Frontend:** `modules/saha/` salt-okunur Cihazlar listesi (`SunucuTablo` + `son_gorulme` + durum/protokol rozeti), RBAC'lı "Saha" menüsü (`saha:oku`), i18n TR/EN, `uretim.eklendi`→cihaz listesi invalidate (canlı `son_gorulme`), Vitest testleri.

## 8. Bağımlılıklar ve Operasyon

- **Yeni Python bağımlılığı:** `aiomqtt>=2` (edge + ingestion). Edge tampon = stdlib `sqlite3` (ek dep yok). `pyproject` ana deps'e eklenir; `testcontainers` (dev, mevcut) MQTT round-trip için yeniden kullanılır.
- **docker-compose:** yeni `ingestion` servisi (`python -m app.ingestion.worker`, `depends_on: [db, redis, mqtt]`). `mqtt` (mosquitto) zaten mevcut. İsteğe bağlı `edge` servisi (demo: simülasyon sürücüsü) override'da.
- **ADR-0010:** `docs/adr/0010-edge-ingestion-mqtt.md` — topic-per-tenant + edge-side agregasyon + store-and-forward + idempotency; ertelenen mTLS/OPC-UA/Modbus gerekçesi.
- **Veri sözlüğü / README / yol-haritası:** `saha_cihazlar`/`saha_alinan_olcum` + S8 ✅ işareti.

## 9. Definition of Done (S8)
- [ ] `ruff`+`mypy` temiz; FE `eslint`+`tsc --strict`+`prettier` temiz.
- [ ] Birim+entegrasyon testleri geçer; edge store-and-forward + ingestion idempotency + **tenant izolasyon** testleri kalıcı.
- [ ] RBAC: `saha:oku/yaz` + `edge` 403/200 testli.
- [ ] API standart zarf + doğru HTTP kodu; `openapi.json` + FE codegen güncel.
- [ ] Migration `public` + 2 tenant şemasında fan-out + downgrade.
- [ ] Yazma uçları audit üretir; ingestion log'u tenant korelasyonlu.
- [ ] ADR-0010 + veri sözlüğü + README/yol-haritası güncel.
- [ ] CI yeşil; Conventional Commit.
- [ ] **Uçtan uca doğrulama:** simüle edge → (canlı yığın) → OEE panosu elle giriş olmadan güncellenir (gerçek tarayıcı/round-trip testi).
