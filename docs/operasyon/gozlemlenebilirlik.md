# Gözlemlenebilirlik — işletim kılavuzu (S19)

Karar ve gerekçeler: [ADR-0040](../adr/0040-gozlemlenebilirlik.md). SLO tanımları: [slo.md](slo.md).

## Kurulum

```bash
# Uygulama yığını + gözlem yığını
mkdir -p infra/alertmanager/gizli
echo "https://<nöbet-kanalı-webhook-adresi>" > infra/alertmanager/gizli/nobet_webhook_url
OTEL_ENDPOINT=http://jaeger:4318 GRAFANA_PAROLA='<güçlü-parola>' \
  docker compose --profile gozlem up -d
```

| Bileşen | Adres | Ne için |
|---|---|---|
| Grafana | http://localhost:3000 (admin / `GRAFANA_PAROLA`) | "FabrikaOS · SLI / SLO" panosu (ana sayfa) |
| Prometheus | http://localhost:9090 | Metrik sorgusu, kural ve alarm durumu (`/alerts`) |
| Alertmanager | http://localhost:9093 | Susturma (silence), gruplama, alıcıya teslim |
| Jaeger | http://localhost:16686 | İstek izleri (`fabrikaos-api`) |
| API metrikleri | http://localhost:8000/metrics | `METRIK_TOKEN` doluysa `Authorization: Bearer …` |

Sentry: `.env` içine `SENTRY_DSN` (proje → Settings → Client Keys). Boşsa kapalıdır.

## Bir hatanın izini sürmek

1. Kullanıcı hata bildirdi ya da alarm geldi → yanıt başlığındaki ya da Sentry olayındaki
   `request_id` etiketini al. (Sentry olayının `tenant` etiketi hangi fabrika olduğunu söyler.)
2. Grafana → Explore → Loki: `{sistem="fabrikaos"} | json | request_id="<id>"` → o isteğin
   tüm log satırları, sırasıyla. Satırdaki `trace_id` ile Jaeger'de isteğin SQL dahil zaman
   çizelgesi açılır.
3. Kişisel veri notu: Sentry'ye istek gövdesi, çerez, `Authorization` ve yığın yerelleri gitmez.
   Bir hatanın girdisine ihtiyaç varsa log'dan (aynı `request_id`) okunur, Sentry'ye eklenmez.

## Alarmlar ve ilk müdahale

### api-erisilemiyor
`FabrikaOSApiErisilemiyor` (kritik): Prometheus API'nin `/metrics` ucunu 2 dakikadır kazıyamıyor.
- `docker compose ps api` ve `docker compose logs --tail 100 api`.
- `curl localhost:8000/saglik` (süreç ayakta mı) ve `/saglik/hazir` (DB/Redis'e ulaşıyor mu;
  503 gövdesi hangi bağımlılığın düştüğünü söyler).
- Süreç ayakta ama hazır değilse sorun bağımlılıktadır: `docker compose ps db redis`.

### hata-butcesi
`FabrikaOSHataButcesiHizliYaniyor` (kritik, 14,4×) / `…YavasYaniyor` (uyarı, 6×): 5xx oranı
erişilebilirlik bütçesini hızla tüketiyor. Yoklama uçları (`/saglik*`) bu orana dahil değildir.
- Panoda "Sunucu hatası veren rotalar" → hangi rota.
- Sentry'de aynı zaman aralığı → en sık hata ve `tenant` etiketi: tek tenant mı, herkes mi?
- Son dağıtımla zamanlama çakışıyorsa önce geri al, sonra incele.

### gecikme
`FabrikaOSGecikmeButcesiYaniyor` (uyarı): GET isteklerinin %30'undan fazlası 300 ms'yi aşıyor.
- `fabrikaos:p95_saniye:5m` (panoda "p95 gecikme · en yavaş 10 rota") → rota.
- Jaeger'de o rotanın yavaş bir izi → SQL span'leri: N+1 mi, eksik indeks mi, kilit beklemesi mi?

### isci-durgun
`FabrikaOSIsciDurgun` (uyarı): bildirim üretici ya da webhook relay 5 dakikadır başarılı tur
yapmadı; outbox birikiyor olabilir.
- `docker compose logs --tail 200 bildirim` (ya da `webhook-relay`): "tenant hatası" satırları.
- Süreç asılıysa yeniden başlatmak güvenlidir: iki işçi de outbox'tan idempotent okur.

### isci-hatalari
`FabrikaOSIsciHatalari` (uyarı): bir işçide 10 dakikada 5'ten fazla hata.
- Sentry'de `tenant` etiketine göre grupla: tek tenant ise o tenant'ın verisi/şeması; hepsi
  ise ortak bağımlılık (DB, SMTP, karşı uç webhook).

## Kurallar değişince

```bash
promtool check rules infra/prometheus/kurallar/fabrikaos.yml
cd infra/prometheus/testler && promtool test rules kurallar_test.yml
amtool check-config infra/alertmanager/alertmanager.yml
```

Yeni alarm = test dosyasına hem tetiklenen hem tetiklenmeyen bir durum. CI (`gozlem-kurallari`
işi) aynı üç komutu koşar. Pano `infra/grafana/panolar/fabrikaos-sli.json`'dan provizyonlanır;
Grafana arayüzünde yapılan değişiklik kalıcı değildir (dosyaya geri yazılmalı).

## Doğrulama kaydı (2026-11-01, yerel, Docker'sız)

Prometheus 3.15.1, Alertmanager 0.34.2, Grafana 13.3.0 ve Jaeger 2.22.0 Windows ikilileriyle:
- Gerçek trafik (%12,5 5xx: Redis'e ulaşamayan hazırlık yoklaması) → `FabrikaOSHataButcesiHizliYaniyor`
  tetiklendi → Alertmanager → yerel webhook alıcısına `firing / kritik` teslim edildi.
- Grafana panosu provizyonla yüklendi, panolar gerçek veriyle doldu (Loki/işçi panelleri o
  turda kaynak olmadığı için boş).
- Jaeger'de istek izi: sunucu span'i (`fabrikaos.tenant`, `fabrikaos.request_id`) + SQL span'i.
- Bu turda görülen iki sorun düzeltildi: yoklama uçları SLI'yı bozuyordu (artık hariç);
  hazırlık yoklamasının `SELECT 1`'i sahipsiz iz üretiyordu (artık bastırılıyor).
- Loki + Alloy yalnız yapılandırma olarak duruyor; Docker'da ilk staging kurulumunda doğrulanacak.
