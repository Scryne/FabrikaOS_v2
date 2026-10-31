# ADR-0042 — Tohumlama ve Onboarding İçe Aktarma (S21)

- **Durum:** Kabul edildi (S21, Faz 5) — pilot fabrika devreye alımı dışa bağlı, açık
- **Tarih:** 2026-11-01
- **İlgili:** şartname §6.6 (tenant yaşam döngüsü: oluştur → migrate → seed → davet → aktifleştir),
  ADR-0018 (entitlement), ADR-0024 (stok bakiyesi/lokasyon), ADR-0041 (göç dağıtımı),
  `docs/uyum/kisisel-veri-envanteri.md`

## Bağlam

Yeni bir fabrikanın ilk haftası boş ekranlarla başlıyordu: makineler, malzemeler, tedarikçiler
ve personel tek tek forma girilecekti. Gerçek bir pilotta bu yüzlerce kayıt demektir ve
müşterinin elinde bu veri zaten Excel'dedir. Ayrıca "kurulum" birkaç ayrı komuttu (public göç,
tenant fan-out, provizyon) ve sırası bilinmeliydi.

## Kararlar

### 1. Tek kurulum komutu, idempotent
`scripts/kurulum.py`: public şema → tenant başına yalıtılmış göç (ADR-0041) → istenirse tenant
provizyonu. İki kez koşmak güvenlidir (ölçüldü: ikinci koşu hiçbir şeyi değiştirmeden çıkar).
Demo verisi ayrı kalır (`demo_verisi.py`; satış/eğitim içindir, pilot tenant'ına girmez).

### 2. İçe aktarma: önizle → hepsi ya da hiçbiri
`/ice-aktarma/{tur}/onizle` hiçbir şey yazmaz; her satır için `yeni` / `guncelle` / `ayni` /
`hata` ve değişen alan adlarını döner. `/uygula` aynı dosyayı yeniden doğrular, **tek satır hatalıysa
hiçbir şey yazmaz** (yarım yüklenmiş ana veri, eksik yüklenmiş veriden daha zor temizlenir).
Eşleştirme anahtarla yapılır (makine/malzeme `kod`, personel `sicil_no`, firma `vergi_no` yoksa
ad): aynı dosyayı ikinci kez uygulamak çift kayıt üretmez. Güncellemede **boş hücre "değiştirme"
demektir**: kısmi bir tabloyla (yalnız durum kolonu) güncelleme yapılabilir.

### 3. Türkiye'deki tablo alışkanlıkları
Türkçe Excel'in CSV'si `;` ayraçlı ve çoğu zaman cp1254 kodludur; ondalık virgüldür. Ayrıştırıcı
BOM'lu/BOM'suz UTF-8 ve cp1254'ü, `;` `,` sekme ayraçlarını, `.xlsx`'i kabul eder; sayılar `1.234,5`
ve `1234.5`, tarihler `31.12.2026` ve `2026-12-31`, mantıksal `evet/hayır`. Başlıklar normalleştirilir
("Sicil No" → `sicil_no`). Şablon BOM + `;` ile iner: Excel'de çift tıkla doğru açılır.

### 4. Tür başına yetki, sıra ve bağımlılık
Her tür kendi yazma iznini ve modülünü ister (personel `ik:yaz` + `ik`); menü bu izinlerden biri
ve bu modüllerden biri açıksa görünür, yetkisiz tür kilitli listelenir. Sıra bağımlılıktan gelir:
firma → malzeme (tedarikçi vergi no ile bağlanır, yoksa satır hatası) → açılış stoğu.

### 5. Açılış stoğu bakiye yazmaz, hareket yazar
Malzeme yüklemesi stok miktarı almaz. Açılış stoğu her satır için bir **giriş hareketi**
(`kaynak=acilis`) yazar; S25 lokasyon/lot bakiyesi, kritik stok olayı ve denetim izi
kendiliğinden işler. İdempotency anahtarı malzeme + lokasyon + lot: ikinci yükleme yeni hareket
yazmaz; farklı miktarla gelirse satır hatası "fark için sayım kullanın" der (açılış stoğu
düzeltme yolu değildir, sayım öyledir).

### 6. KVKK
Önizleme ve uygulama yanıtları değer taşımaz (anahtar, işlem, alan adı, hata). Personel
dosyasındaki T.C. kimlik no sağlama kuralıyla doğrulanır ama yanıta, dolayısıyla tarayıcı
belleğine girmez (testli). Uygulama denetim izine yazılır (dosya adı + sayılar).

## Sonuçlar
- (+) Pilotun ilk günü: kurulum tek komut, ana veri müşterinin kendi Excel'inden dakikalar içinde.
- (+) 12 backend testi (5 mutasyonun 5'i yakalandı), 3 bileşen testi; ekran turu 1440/390 taşmasız.
- (−) Ortak (CRM kişi), ürün/reçete, kullanıcı hesabı içe aktarımı yok; S27'nin genel CSV/XLSX
  çerçevesi bu modülün ayrıştırıcı ve önizleme sözleşmesini yeniden kullanmalı.
- **Açık (dışa bağlı):** pilot fabrika devreye alımı ve gerçek veriyle çalıştırma — bir müşteri
  ve sözleşme gerektirir. Hazırlık listesi: `docs/operasyon/pilot.md`.
