# SLI / SLO tanımları

Kaynak gereksinimler: şartname NFR-01 (tipik liste/okuma uçları p95 < 300 ms) ve NFR-03
(uptime ≥ %99,5). Ölçüm ve alarm uygulaması: [ADR-0040](../adr/0040-gozlemlenebilirlik.md),
`infra/prometheus/kurallar/fabrikaos.yml`.

| SLO | SLI (Prometheus) | Hedef | Pencere | Hata bütçesi |
|---|---|---|---|---|
| SLO-1 Erişilebilirlik | 5xx olmayan isteklerin oranı (`fabrikaos:sli_hata_orani:*` tümleyeni) | ≥ %99,5 | 30 gün (kayan) | %0,5 ≈ 3 sa 36 dk tam kesinti |
| SLO-2 Gecikme | 300 ms altında tamamlanan GET oranı (`fabrikaos:sli_yavas_orani:*` tümleyeni) | ≥ %95 | 30 gün (kayan) | %5 |

**Kapsam.** Tüm API rotaları; yoklama uçları (`/saglik`, `/saglik/hazir`) ve `/metrics` hariç.
4xx istemci hatasıdır, bütçeyi tüketmez. Kimlik doğrulama isteklerinin (argon2id, bilinçli
olarak yavaş) gecikmesi POST olduğu için SLO-2'ye girmez.

**Ölçüm noktası.** Uygulama içi (`MetrikMiddleware`). Traefik'in önündeki kesinti (TLS, DNS,
ağ) bu SLI'da görünmez; dış yoklama (blackbox/uptime servisi) ilk prod kurulumunda eklenir.

## Alarm politikası (çok pencereli yanma hızı)

| Alarm | Koşul | Önem | Anlamı |
|---|---|---|---|
| Hızlı yanma | 1 sa ve 5 dk hata oranı > 14,4 × %0,5 | kritik | Bu hızla 30 günlük bütçe ~2 günde biter |
| Yavaş yanma | 6 sa ve 30 dk hata oranı > 6 × %0,5 | uyarı | Bütçe ~5 günde biter |
| Gecikme | 1 sa ve 5 dk yavaş oran > 6 × %5 | uyarı | GET'lerin %30'undan fazlası 300 ms üstü |

Kısa pencere alarmın sorun bitince hızla kapanmasını sağlar; uzun pencere tek bir sıçramanın
nöbetçiyi uyandırmasını engeller.

## Bütçe tükenirse

Kalan bütçe panoda "Kalan bütçe · 30 gün". Sıfırın altına inerse pencere toparlanana kadar
yeni özellik dağıtımı yerine güvenilirlik işi (hata düzeltme, geri alma, kapasite) önceliklidir.
Bu bir ekip anlaşmasıdır; pilot/GA öncesi müşteri SLA'sına dönüştürülmeden önce en az bir tam
30 günlük ölçüm penceresi beklenir.
