# Güvenlik taraması ve kapasite ölçümü (S22)

Kararlar: [ADR-0043](../adr/0043-sertlestirme-kapasite.md). NFR-01: tipik liste/okuma uçları
**p95 < 300 ms**. NFR-05: OWASP Top 10 önlemleri.

## Statik güvenlik taraması (bandit 1.8, 2026-11-01)

`bandit -r backend/app`: yüksek 0, orta 22, düşük 14. CI'da orta ve üstü kapıdır
(`bandit -ll -s B608`).

| Bulgu | Adet | Karar |
|---|---|---|
| B608 SQL'e metin birleştirme | 22 | Tek tek incelendi, hepsi güvenli. Birleştirilen değerler: sunucu tarafı beyaz liste (`enerji/repository.py:82`, `time_bucket` aralığı), `sema_adi()` ile doğrulanmış şema adı (`uyum/service.py`, `platform/service.py`, `operasyon/*`), `information_schema`'dan gelen ve tırnaklanan tablo/sütun adı (`platform/ihrac.py`, `operasyon/yedek.py`), sabit maske ifadeleri (`operasyon/anonim.py`). Kullanıcı girdisi her yerde bağlı parametredir. CI'da yalnız bu kural atlanır; yeni bir SQL birleştirme kod incelemesinde gerekçelendirilir. |
| B101 `assert` | 13 | Tip daraltma (`assert x is not None` sonrası ORM nesnesi). Hiçbiri yetki ya da doğrulama yapmıyor; `-O` ile kalksalar davranış değişmez. |
| B105 sabit parola dizgesi | 1 | `config.VARSAYILAN_SECRET`: üretimde `_guvenlik_dogrula` bu değerle açılışı reddeder (testli). |

**Yapılmadı:** OWASP ZAP dinamik taraması (Java/Docker gerektirir) ve dış pentest. İlk staging
kurulumunda ZAP baseline koşulur, bulguları bu tabloya eklenir.

## Kapasite (k6 2.3.0, demo tenant'ı, 16 liste/özet ucu)

Ortam: geliştirici dizüstü (Windows), PostgreSQL 16 + TimescaleDB aynı makinede, tek tenant,
demo verisi. Senaryo: `perf/k6/nfr01_liste.js` (tek giriş, her sanal kullanıcı 16 ucu sırayla).

| Yapılandırma | Eşzamanlı kullanıcı | İstek/sn | p95 | En yavaş uç p95 | Hata | NFR-01 |
|---|---:|---:|---:|---:|---:|---|
| 1 işçi | 20 | 120 | 181 ms | 220 ms (`/makineler`) | %0 | ✅ |
| 1 işçi | 50 | 126 | 469 ms | 512 ms | %0 | ❌ (kuyruk) |
| 4 işçi | 50 | 340 | 154 ms | — | %0 | ✅ |

**Çıkarım.** Tek süreç ~125 istek/sn'de CPU'ya dayanıyor; gecikme yükü artınca istek işleme değil
kuyruk büyüyor. Uvicorn işçi sayısı ile neredeyse doğrusal ölçekleniyor. Üretim katmanı
(`docker-compose.prod.yml`) 4 işçiyle açılır (`API_ISCI`). Çok işçide Prometheus sayaçları
paylaşılan dizinden toplanır; ölçümde 4 işçiye dağılan 200 isteğin üç ayrı `/metrics`
okumasında da 200 göründüğü doğrulandı.

Ölçüm tek tenant ve küçük veriyledir. 50 tenant (NFR-02) ve büyük hypertable'lar için tekrar
koşulmalı; `uretim_verileri` sıkıştırma/saklama politikası henüz yok (S3 notu).

```bash
k6 run -e API=https://staging.example -e TENANT=demo -e EPOSTA=... -e PAROLA=... \
  -e VU=50 -e SURE=120s perf/k6/nfr01_liste.js
```
