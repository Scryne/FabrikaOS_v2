# Olay müdahale — runbook (S28)

Bir alarm çaldığında ya da bir müşteri "sistem çalışmıyor" dediğinde izlenen süreç. Alarm başına
teknik ilk adımlar [gozlemlenebilirlik.md](gozlemlenebilirlik.md#alarmlar-ve-ilk-müdahale)'de,
veri geri yükleme [dr.md](dr.md)'de; bu belge ikisinin üstündeki karar ve iletişim katmanıdır.
Nöbet düzeni: [nobet.md](nobet.md). Hedefler: [slo.md](slo.md).

## 1. Önem derecesi

İlk 10 dakikada belirlenir; bilgi arttıkça yükseltilip düşürülebilir. Kararsızsan bir üst dereceyi seç.

| Derece | Ne demek | Örnek | İlk yanıt | Güncelleme sıklığı |
|---|---|---|---|---|
| **Ö1** | Tüm tenant'lar ya da bir tenant'ın tamamı çalışamıyor; veri kaybı/sızıntı şüphesi | API erişilemiyor, çapraz tenant veri görünmesi, yanlış yedeğe dönüş | 15 dk | 30 dk |
| **Ö2** | Bir modül ya da kritik akış çalışmıyor, geçici yol yok | İş emri başlatılamıyor, saha ölçümleri yazılmıyor, giriş yapılamıyor | 30 dk | 1 sa |
| **Ö3** | İşlev bozuk ama geçici yol var; performans bütçe dışında | Rapor PDF'i üretilmiyor, liste uçları 300 ms üstü, bildirimler gecikmeli | 4 iş saati | günlük |
| **Ö4** | Kozmetik ya da tek kullanıcıyı etkileyen sorun | Yanlış etiket, tek tarayıcıda görünüm hatası | sonraki sprint | — |

**Güvenlik olayı** (yetkisiz erişim, sızan anahtar, şüpheli denetim kaydı) her zaman en az Ö2'dir
ve §5'teki ek adımlar uygulanır. Kişisel veri ihlali şüphesi Ö1'dir.

## 2. Roller

Küçük ekipte bir kişi birden çok rolü taşıyabilir; Ö1'de olay yöneticisi ile teknik müdahale
eden aynı kişi olmamalıdır.

- **Olay yöneticisi (OY):** dereceyi belirler, kimin ne yaptığını yönetir, karar kaydını tutar.
  Kendisi komut çalıştırmaz.
- **Teknik müdahale:** teşhis ve düzeltme. Yaptığı her değişikliği olay kanalına yazar
  (komut, saat, sonuç).
- **İletişim:** müşteriye ve iç paydaşlara güncellemeyi §4'teki şablonla, §1'deki sıklıkla gönderir.

## 3. Akış

1. **Kabul et** (alarm Alertmanager'dan `nobet` alıcısına düşer): alarmı sahiplen, olay kanalını
   aç (`#olay-YYYYMMDD-kisa-ad`), dereceyi yaz.
2. **Etkiyi ölç:** hangi tenant'lar, hangi modüller, ne zamandan beri? Grafana "FabrikaOS · SLI /
   SLO" panosu → "Sunucu hatası veren rotalar"; Loki'de `tenant` ve `request_id` ile; Sentry'de
   tenant etiketiyle. Tek tenant mı, hepsi mi: bu ayrım çoğu kararın yarısıdır.
3. **Önce durdur, sonra düzelt.** Sırayla dene: son dağıtımı geri al (`docker compose` önceki
   imaj etiketi; göç geri alma [dr.md §3](dr.md#3-göç-dağıtımı-ve-geri-alma)) → etkilenen
   özelliği kapat (Platform › Tenant › Özellik bayrakları, anında etkili) → tenant'ı askıya al
   (yalnız veri sızıntısı şüphesinde). Kök neden bulunmadan "düzelttim" deme.
4. **Doğrula:** SLI panosunda 5xx oranı ve gecikme normale döndü mü; etkilenen akışı gerçek bir
   kullanıcı hesabıyla (müşteri onayıyla) baştan sona dene.
5. **Kapat:** müşteriye son güncelleme, olay kanalında zaman çizelgesi; Ö1/Ö2 için 5 iş günü
   içinde olay sonrası inceleme (§6).

## 4. İletişim şablonları

**İlk bildirim (derece belirlenince):**

> **[Ö2] Saha ölçümleri sisteme yazılmıyor — inceleniyor.** 14:05'ten beri makinelerden gelen
> ölçümler panoya düşmüyor; elle girilen kayıtlar etkilenmiyor. Ölçümler kaybolmuyor, cihazlarda
> bekliyor (QoS 1). Bir sonraki güncelleme 15:00'te.

**Güncelleme:** ne biliyoruz, ne yapıyoruz, müşterinin yapması gereken bir şey var mı, sonraki
güncellemenin saati. **Kapanış:** ne oldu (bir cümle), ne zaman düzeldi, veri etkisi (kayıp
var/yok, kanıtıyla), kalıcı önlem ne zaman.

Belirsizliği saklama: "kök neden henüz bilinmiyor" geçerli bir güncellemedir. Veri kaybı
konusunda emin olmadan "kayıp yok" deme.

## 5. Güvenlik olayı ek adımları

1. Kanıtı koru: ilgili zaman aralığının denetim kaydını (Yönetim › Denetim Kayıtları, CSV
   dışa aktarma) ve Loki loglarını dışa al; sunucuyu yeniden kurmadan önce.
2. Sızan sırrı **önce döndür, sonra temizle**: JWT imza anahtarı (tüm oturumları düşürür), API
   anahtarı (Yönetim › Webhooklar & API › iptal), webhook sırrı, OIDC client secret, veritabanı
   parolası. Git geçmişinden silmek yetmez; sızmış sayılır.
3. Etkilenen kullanıcıların oturumlarını kapat (kullanıcı › oturumlar) ve parola sıfırlat.
4. Kişisel veri ihlali şüphesinde veri sorumlusunu (müşteri) derhal bilgilendir; bildirim
   yükümlülüğü ve süresi müşterinin hukuk biriminin kararıdır, ürün ekibinin değil.

## 6. Olay sonrası inceleme (suçlamasız)

Ö1 ve Ö2 için zorunlu; şablon `docs/operasyon/olaylar/YYYY-MM-DD-kisa-ad.md`:

```markdown
# <Olay adı> — <tarih>
**Derece:** Ö? · **Süre:** başlangıç → tespit → hafifletme → çözüm · **Etki:** tenant/modül/kullanıcı, veri etkisi

## Zaman çizelgesi (UTC+3)
## Kök neden (5 neden; kişi değil süreç/sistem)
## Ne iyi gitti / ne kötü gitti / nerede şanslıydık
## Aksiyonlar (sahip, tarih, takip bağlantısı) — en az biri "aynı sınıf tekrar olursa erken yakala"
```

Her aksiyon bir teste, alarma ya da runbook değişikliğine dönüşmeden inceleme kapanmaz.
Hata bütçesi tüketimi [slo.md](slo.md#bütçe-tükenirse) kuralına göre değerlendirilir.

## 7. Bağımlılık kesintisinde beklenen davranış (S28 testli)

Bir altyapı parçası düştüğünde ürünün ne yaptığı `backend/tests/test_s28_dayaniklilik.py` ile
sabitlenmiştir. Olay sırasında "bu normal mi" sorusunun cevabı:

| Kesinti | Kullanıcı ne görür | Veri | Ne yapılır |
|---|---|---|---|
| **Redis** | Giriş ve tüm okuma/yazma çalışır. Oturum yenileme 503 `HIZMET_KULLANILAMAZ` (erişim token'ı süresince oturum sürer). Gerçek zamanlı panolar güncellenmez. `/saglik/hazir` 503 → yük dengeleyici trafiği keser. | Kayıp yok. Oran sınırı süreç içi yedek sayaca geçer (işçi başına; N işçide sınır en çok N kat gevşer). | Redis'i ayağa kaldır; uygulama yeniden başlatma gerektirmez. |
| **Nesne deposu (MinIO)** | Belge sürümü yükleme 503 ("dosya kaydedilmedi"); belge kaydı açılmaz. Diğer modüller etkilenmez. | Yarım sürüm kaydı oluşmaz. | Depoyu kaldır; kullanıcı yüklemeyi tekrarlar. |
| **MQTT broker** | Saha ölçümleri panoya düşmez. | Kayıp yok: alım işçisi kalıcı oturum (`clean_session=False`, sabit istemci kimliği) ve QoS 1 ile yeniden bağlanır; broker birikmiş mesajları teslim eder. Tekrar gelen ölçüm idempotent. | Broker'ı kaldır; işçi üstel bekleme ile (en çok 30 sn) kendisi bağlanır. |
| **Veritabanı (geçici)** | 5xx. | Alım işçisi mesajı düşürmez: 0,5 → 15 sn arası altı deneme. Süre aşılırsa mesaj broker'da kalır. | Bağlantı/havuz sorununu çöz; kalıcıysa [dr.md](dr.md). |
