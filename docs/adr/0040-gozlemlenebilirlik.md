# ADR-0040 — Gözlemlenebilirlik: Metrik, Hata İzleme, Dağıtık İz, SLO Alarmları (S19)

- **Durum:** Kabul edildi (S19, Faz 5)
- **Tarih:** 2026-10-31
- **İlgili:** NFR-01 (p95 < 300 ms), NFR-03 (uptime ≥ %99,5), NFR-09 (yapısal log + Sentry +
  Prometheus/Grafana), şartname §6.4; ADR-0021 (bildirim işçisi), ADR-0020 (webhook relay)
- **Numara notu:** 0025–0031 yol haritasında S26–S32'ye, 0032–0039 mobil plana ayrılmıştır;
  Faz 5 kararları 0040'tan başlar.

## Bağlam

S1'den beri JSON log satırı `request_id` + `tenant` taşıyordu, ama üretimde bir hatanın
görülmesi, hızın ölçülmesi ve bir şey bozulunca birinin haberdar edilmesi için hiçbir yol yoktu.
Hazırlık ucu (`/saglik/hazir`) bağımlılıklara bakmadan her zaman "hazır" diyordu. Kabul
kriteri: hata Sentry'de tenant/istek bağlamıyla görünür, SLI/SLO panoları yayında, alarm tetiklenir.

## Kararlar

### 1. Metrikler: rota şablonu etiketi, tenant etiketi yok
`MetrikMiddleware` (saf ASGI) istek sayısını `(yontem, rota, durum)` ve süreyi `(yontem, rota)`
etiketleriyle üretir. `rota` Starlette'in eşleştirdiği **şablondur** (`/api/v1/makineler/{makine_id}`);
eşleşmeyen yol `eslesmeyen` olur. Ham yol her kimlik için yeni bir zaman serisi açar, 404 taraması
Prometheus'u şişirirdi. **Tenant etiket olarak yazılmaz:** ≥50 tenant × ~300 rota × durum
kardinalitesi tek düğüm Prometheus için fazla; tenant kırılımı log ve izde.
Katman, hata katmanının (`BeklenmeyenHataMiddleware`) **dışındadır**: o katmanın ürettiği 500'ler
SLI'ya sayılır (testli). Süre kovalarında 0,3 s bir sınırdır: "300 ms altı oran" tahminsiz okunur.

İşçiler (ingestion, bildirim, webhook relay) aynı defteri `ISCI_METRIK_PORTU` üzerinden açar:
`fabrikaos_isci_mesajlari_total{isci,sonuc}` ve `fabrikaos_isci_son_basari_zamani{isci}`.

### 2. SLO ve alarm: çok pencereli yanma hızı
- **SLO-1 (NFR-03):** 30 günde isteklerin ≥ %99,5'i 5xx olmadan. Bütçe 0,005.
- **SLO-2 (NFR-01):** GET isteklerinin ≥ %95'i 300 ms altında. Bütçe 0,05.

Eşik alarmı ("5xx > %1") ya gürültü üretir ya geç kalır; Google SRE Workbook'un çok pencereli
yanma hızı kullanılır: hızlı yanma 14,4× (1 sa ve 5 dk birlikte) → kritik, yavaş yanma 6×
(6 sa ve 30 dk) → uyarı. Kısa pencere, sorun bittiğinde alarmın hızla kapanmasını sağlar.
Ayrıca: API kazınamıyor (2 dk), işçi durgun (bildirim/relay 5 dk başarısız tur; ingestion
boşta kalabileceği için hariç), işçi hata patlaması.
Yoklama uçları (`/saglik*`) SLI dışıdır: hazırlık yoklaması bağımlılık düşünce 2 sn zaman aşımıyla
503 döner; SLI'ya girince p95'i ve hata oranını kullanıcı deneyiminden bağımsız bozuyordu (canlı
turda görüldü). Kurallar `promtool test rules` ile birim testlidir (her alarm tetiklenen ve
tetiklenmeyen seriyle); kurallara uygulanan 6 mutasyonun 6'sı testte yakalandı.

### 3. Sentry: bağlam etiketi + gizli veri temizliği
DSN varsa kurulur, yoksa hiçbir şey yapmaz. `before_send` her olaya `tenant` (doğrulanmışsa
çözümlenmiş tenant, yoksa ham başlık) ve `request_id` ekler; aynı `request_id` log satırında ve
yanıt başlığında olduğu için Sentry'deki hatadan isteğin tüm loglarına gidilir. Hata katmanı
istisnayı yakalayıp 500 zarfına çevirdiği için Sentry'nin kendi entegrasyonu onu görmez;
`hata_bildir` açıkça çağrılır (tek olay, testli).

**KVKK:** `send_default_pii=False`, istek gövdesi hiç gönderilmez, `Authorization`/`Cookie`/
API anahtarı başlıkları ve sorgu dizesindeki token'lar maskelenir, **yığın çerçevesi yerelleri
kapalıdır** (`include_local_variables=False`). Sonuncusu testle bulundu: ASGI `scope` yerel
değişkeni ham `Authorization` başlığını olaya taşıyordu.

### 4. OpenTelemetry: isteğe bağlı, kapalıyken bedava
`OTEL_ENDPOINT` tanımlıysa FastAPI ve SQLAlchemy span'leri OTLP/HTTP ile gider; değilse API
no-op sağlayıcıyla çalışır. Sunucu span'ine `fabrikaos.tenant` ve `fabrikaos.request_id`
yazılır; JSON log satırına `trace_id` eklenir. Sağlık ve metrik yolları iz üretmez.
`opentelemetry-instrumentation-sqlalchemy` "sqlalchemy < 2.1" bildiriyor ve kurulu 2.1 ile
**sessizce hiçbir şey yapmıyordu**; bağımlılık denetimi atlanır (`skip_dep_check=True`),
2.1 ile SQL span'i testli ve canlı Jaeger turunda görüldü.

### 5. Hazırlık ucu gerçek bağımlılıklara bakar
`/saglik/hazir` veritabanı (`SELECT 1`) ve Redis (`PING`) yoklamalarını paralel, her biri
2 sn zaman aşımıyla koşar; biri düşerse **503 + `success: false`** ve hangi bağımlılığın
düştüğü (hata türüyle, bağlantı dizesi olmadan) döner. Liveness (`/saglik`) bağımlılığa
bakmaz: DB kesintisinde orkestratör süreci öldürüp yeniden başlatmamalı.

### 6. Yığın: compose `gozlem` profili
Prometheus 3.15.1 + Alertmanager 0.34.2 + Grafana 13.3.0 (provizyonlu "FabrikaOS · SLI / SLO"
panosu) + Loki 3.7.9 + Alloy 1.21.3 (Docker log toplama) + Jaeger 2.22.0. Alertmanager'ın nöbet
webhook adresi depoda tutulmaz (`infra/alertmanager/gizli/`, `.gitignore`).

## Sonuçlar
- (+) Kabulün üç ayağı yerelde kanıtlandı: Sentry olayı tenant/request_id ile (test), gerçek 503
  trafiğiyle Prometheus → Alertmanager → webhook alarmı (canlı), pano ve izler (canlı).
- (+) Alarm kuralları kod gibi test edilir; CI'da `promtool test rules` koşabilir.
- (−) Loki/Alloy yalnız yapılandırma olarak doğrulandı; Docker ortamında koşturulmadı
  (makinede Docker test için açılmıyor). İlk staging kurulumunda doğrulanacak.
- (±) Çok işçili uvicorn: S22'de çok süreç modu eklendi (`PROMETHEUS_MULTIPROC_DIR`), `/metrics`
  bütün işçilerin toplamını verir (ADR-0043).
- **Açık:** Sentry projesi ve DSN (ücretsiz katman yeterli, şartname §11) hesap açılınca;
  platform panelinde "kuyruk sağlığı / hata oranı" kartları Prometheus'tan okunabilir (S27).
