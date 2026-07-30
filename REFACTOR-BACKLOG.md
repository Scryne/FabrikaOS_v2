# REFACTOR-BACKLOG

Bu dosya, **modül maratonu** sırasında tespit edilen ama maratonu durdurmamak için
uygulanmayan değişikliklerin kaydıdır. Kullanıcı bu listeyi maraton bitiminde **tek
parti hâlinde** gözden geçirecektir (2026-07-30 tarihli talimat).

## Buraya ne yazılır?

1. **Kırıcı (breaking) değişiklik önerileri** — mevcut API sözleşmesini, alan adlarını,
   endpoint yapısını veya yanıt şeklini değiştirecek her şey.
2. **Mevcut uçlarda doğrulama sıkılaştırması** — Pydantic sınır/desen/ondalık hassasiyet/
   tarih tutarlılığı eklemeleri. Şema *şekli* değişmese bile davranışsal kırıcı değişikliktir:
   bugün kabul edilen bir gövde yarın 422 döner. **Yalnız bu maratonda yeni eklenen uçlarda
   doğrudan uygulanır**; maraton öncesi var olan uçlarda buraya yazılır.

## Buraya ne YAZILMAZ (doğrudan uygulanır)?

- Eklemeli (additive) sertleştirme: indeks, CHECK/UNIQUE/NOT NULL kısıtı (veri denetimi +
  backfill ile birlikte), `ondelete` semantiği, `selectinload` ile N+1 giderme, tipleme,
  saf fonksiyon ayrıştırması, hata yönetimi, servis/repository ayrımı.
- Bu maratonda **yeni yazılan** uçlardaki her türlü doğrulama sıkılaştırması.

## Girdi biçimi

Her girdi şu dört başlığı doldurur:

- **Mevcut tasarım** — bugün ne var.
- **Neden yanlış** — hangi somut sorun/risk.
- **Önerilen değişiklik** — ne yapılmalı.
- **Etki alanı (blast radius)** — etkilenen uçlar, FE bileşenleri, openapi tüketicileri
  (codegen tipleri, dış API anahtarı istemcileri, webhook alıcıları, mobil plan).

---

## Girdiler

### 1. KVKK anonimleştirmesi ile yasal saklama yükümlülüğü çakışması (S29 sonrası ele alınmalı)

*Kaydeden: kullanıcı yönlendirmesi, 2026-07-30 (S23 kapanışı). İleriye dönük not.*

- **Mevcut tasarım.** `POST /kvkk/anonimlestir` kişinin kimlik alanlarını **geri
  alınamaz** biçimde maskeler (`kullanici`: e-posta/ad + hesap pasif; `personel`:
  ad/soyad/TC/telefon/e-posta/doğum tarihi). Denetim izinin adli çekirdeği korunur ama
  **mali kayıtlar bugün kapsamda değil** — çünkü henüz `finans` modülü yok.
- **Neden yanlış (olacak).** S29 ile `finans` modülü gelince cari hesap, fatura ve
  tahsilat/ödeme kayıtları kişiye/firmaya bağlanacak. Türk mevzuatında fatura ve ticari
  defter kayıtları için **yasal saklama süresi** vardır (VUK/TTK; 5–10 yıl aralığı).
  KVKK m.7'deki silme hakkı, **başka bir kanunda öngörülen saklama yükümlülüğünü ortadan
  kaldırmaz**. Bugünkü "her şeyi maskele" yaklaşımı S29 sonrası olduğu gibi çalışırsa
  saklanması zorunlu mali veriyi bozabilir ve şirketi mevzuata aykırı duruma düşürebilir.
- **Önerilen değişiklik.** Anonimleştirmeyi **alan bazlı politikaya** çevir:
  (a) yasal saklama kapsamındaki tablo/kolonlar maskelenmez, **kısıtlı erişime** alınır ve
  saklama süresi sonunda imha kuyruğuna girer; (b) `anonimlestir` çıktısına "korunan
  kayıtlar" raporu eklenir (kişiye hangi verinin hangi hukuki sebeple saklandığı
  bildirilebilsin — KVKK aydınlatma yükümlülüğü); (c) saklama süresi dolunca otomatik
  imha eden zamanlanmış tarama (mevcut `*-tara` kenar-tetik deseni).
- **Etki alanı.** `POST /kvkk/anonimlestir` (davranış değişir: artık "her şeyi maskele"
  değil), `uyum/service.anonimlestir`, S29 `finans` modelleri (fatura/cari/ödeme),
  `docs/uyum/kisisel-veri-envanteri.md` (saklama süresi sütunu eklenmeli), FE `/kvkk`
  ekranı (korunan kayıt raporu). Dış tüketici yok; openapi yanıtı genişler, kırılmaz.
- **Ne zaman.** S29 (Finans) **tamamlandıktan hemen sonra**, S31'den önce: mali veri
  üretilmeye başlamadan politika yerinde olmalı.
