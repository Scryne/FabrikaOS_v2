# Nöbet (on-call) düzeni (S28)

Kim, ne zaman, hangi alarmla uyandırılır ve nöbet nasıl devredilir. Olay sırasında izlenecek
süreç: [olay-mudahale.md](olay-mudahale.md).

## Alarm yönlendirmesi

Kaynak `infra/alertmanager/alertmanager.yml`. Tüm alarmlar `nobet` alıcısına gider; gruplama
`alertname` + `isci`.

| Önem etiketi | Alarm | Tekrar | Kime |
|---|---|---|---|
| `kritik` | `FabrikaOSApiErisilemiyor`, `FabrikaOSHataButcesiHizliYaniyor` | 1 sa | Nöbetçi, gece dahil (telefon/çağrı) |
| `uyari` | `FabrikaOSHataButcesiYavasYaniyor`, `FabrikaOSGecikmeButcesiYaniyor`, `FabrikaOSIsciDurgun`, `FabrikaOSIsciHatalari` | 4 sa | Nöbetçi, mesai içinde; gece yalnız sabah bakılır |

Alıcının teslim kanalı (e-posta, çağrı servisi webhook'u) kuruluma özeldir ve
`infra/alertmanager/gizli/` altındaki dosyadan okunur; depoya girmez. Yeni bir kurulumda ilk iş
test alarmı göndermek ve nöbetçinin gerçekten aldığını görmektir:

```bash
amtool alert add FabrikaOSTestAlarmi onem=kritik --annotation=ozet="Nöbet hattı testi" \
  --alertmanager.url=http://localhost:9093
```

## Rotasyon

- Haftalık, pazartesi 10:00 devir. Birincil + ikincil nöbetçi; birincil 15 dakikada kabul
  etmezse ikincil, o da 15 dakikada etmezse ekip lideri.
- Nöbetçi dağıtım yapma yetkisine ve [dr.md](dr.md) adımlarını uygulayacak erişime sahip olur
  (sunucu, veritabanı yedek dizini, Platform paneli).
- Nöbet haftasında büyük özellik işi planlanmaz; alarm gürültüsünü azaltmak ve bir önceki
  olayların aksiyonları önceliklidir.

## Devir notu (her pazartesi)

```markdown
## Nöbet devri — <tarih>
- Açık olaylar / izlenen riskler:
- Bu hafta çalan alarmlar (ad, sayı, gerçek mi gürültü mü):
- Hata bütçesi: erişilebilirlik %…, gecikme %… (Grafana › Kalan bütçe · 30 gün)
- Yaklaşan bakım/dağıtım/tatbikat:
- Gürültü aksiyonu (eşik, `for:` süresi ya da kural değişikliği önerisi):
```

Aynı alarm iki hafta üst üste "gürültü" diye işaretlenirse kural değiştirilir ya da silinir;
nöbetçinin görmezden gelmeyi öğrendiği alarm, gerçek olayda da görmezden gelinir. Kural
değişikliği promtool testiyle birlikte yapılır ([gozlemlenebilirlik.md](gozlemlenebilirlik.md#kurallar-değişince)).

## Nöbetçinin cep kartı

1. Alarmı kabul et, olay kanalını aç, dereceyi yaz.
2. Grafana "FabrikaOS · SLI / SLO": tek tenant mı, hepsi mi; hangi rota?
3. Son 2 saatte dağıtım var mı? Varsa önce geri al.
4. Bağımlılık mı? `/saglik/hazir` hangi bileşeni `false` gösteriyor (veritabanı, Redis)?
   Beklenen davranış: [olay-mudahale.md §7](olay-mudahale.md#7-bağımlılık-kesintisinde-beklenen-davranış-s28-testli).
5. 30 dakikada hafifletemediysen ikincili çağır. Yardım istemek derece yükseltmek değildir.
