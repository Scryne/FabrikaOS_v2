# ADR-0046 — Platform Deneyimi II: Dışa Aktarma, Yazdırma, Erişilebilirlik Pası (S27-B)

- **Durum:** Kabul edildi (S27-B, Faz 6)
- **Tarih:** 2026-11-01
- **İlgili:** ADR-0045 (S27-A), ADR-0016 (rapor üretimi, async 202), ADR-0024 (satınalma siparişi),
  `uiplani.md` §11.3, WCAG 2.1 AA

## 1. Liste dışa aktarma: istemcide, mevcut liste ucundan

`SunucuTablo`'ya isteğe bağlı `disaAktar` verilir; menü ekrandaki arama/süzgeç/sıralamayla aynı
liste ucunu 100'lük sayfalarla gezer ve CSV ya da Excel indirir. 23 liste ekranında açık.

- **Sınır 5.000 satır.** Aşılırsa ilk 5.000 iner ve kullanıcıya toplamla birlikte söylenir;
  sessizce kesilmez. Daha büyük dışa aktarım rapor modülünün async 202 yoludur (ADR-0016).
- **CSV Türk Excel'ine göre:** `;` ayraç, ondalık virgül, UTF-8 BOM. `= + - @` ile başlayan metin
  tek tırnakla etkisizleştirilir (CSV/formül enjeksiyonu); negatif sayılar sayı kalır.
- **Excel** `write-excel-file` (MIT, 4.1.1) ile; yalnız ilk kullanımda yüklenen ayrı parça.
- **Sütunlar tablodan türetilir:** başlığı metin olan ve `dataIndex` ya da `key` taşıyan sütunlar.
  İndirme anında hiç değeri olmayan sütun düşer, `kod`'a bağlı sütun "Kod" adını alır, kayıtta
  kimlik alanı (kod, ad, ad soyad, başlık) varsa başa eklenir. İlk denemede malzeme listesinin
  "Ad" sütunu aslında `kod`'u gösteriyordu; kural bu yüzden var.

Reddedilen: her liste ucuna `?bicim=xlsx` eklemek. 23 ucu değiştirirdi; yetki, süzgeç ve sayfalama
zaten liste ucunda doğru, istemci aynı ucu kullanınca RBAC kendiliğinden korunur.

## 2. Sipariş formu PDF'i

`GET /satinalma-siparisleri/{id}/pdf` (`satinalma:oku`): alıcı ve tedarikçi künyesi, kalem
tablosu, Türkçe sayı biçimi, ara toplam, üç imza alanı, sayfa altbilgisi. Fiyatı girilmemiş kalem
"—" yazar, toplam "*" ile işaretlenir ve dipnot düşer: eksik fiyat sessizce 0 sayılmaz. Her
indirme denetim izine `disa_aktar` olarak yazılır. Sipariş detayında "Sipariş formu (PDF)".

## 3. Yazdırma stil sayfası

`@media print`: kabuk, gezinme, düğmeler, sayfalama ve süzgeçler gizlenir; renk değişkenleri
kâğıt için yeniden tanımlanır (koyu temanın açık metinleri beyaz kâğıtta görünmüyordu — ilk baskı
denemesinde başlık ve KPI sayıları kaybolmuştu), tablo satırı bölünmez, başlık her sayfada tekrar
eder. Her liste ve detay ekranı Ctrl+P ile A4'e uygun çıkar.

## 4. Erişilebilirlik pası (axe-core, WCAG 2.1 AA)

11 ana ekran oturum açık halde axe-core 4.10 ile tarandı. Bulunan ve düzeltilenler:

| Bulgu | Neden | Düzeltme |
|---|---|---|
| Kontrast 3,83:1 (her sayfa) | Menü grup başlığı `#6d6d74` sabit | `metin-soluk` token'ı |
| Kontrast 4,44 / 3,68 | Logo "OS", avatar, tarih rozeti `--mavi` metin | Yeni token `mavi-metin` `#6b8ff8` |
| Kontrast 3,75 | antd koyu algoritmasında tehlike düğmesi metni | Button `colorError` = `hata-metin` `#f26b6b` |
| Kontrast 3,28 | Seçili sekme metni | Tabs `itemSelectedColor` = `mavi-metin` |
| Kontrast 3,38 | Hazır mor/mavi etiketler | Onay kutusunda açık tonlu özel etiket |
| `role="img"` adsız | ECharts kapsayıcısı | `EGrafik` `etiket` → seçenek başlığı → "Grafik" |
| Etiketsiz `select` | Liste süzgeçleri | `aria-label` |
| Adsız ilerleme çubuğu | Sipariş teslim ilerlemesi | `aria-label` |

Son tarama: 11/11 ekran temiz. `DESIGN.md`'ye `mavi-metin` ve `hata-metin` eklendi: dolgu ve çizgi
için `mavi`/`hata`, koyu zeminde metin için `-metin` tonları.

## 5. İş takvimi "bugün"ü (bulunan kusur)

S27 tam test koşusu UTC gece yarısını (TR 03:00) geçerken bir S26-A testi düştü: test ile sunucu
farklı "bugün" görüyordu. Kök neden testte değil üründeydi: 14 yerde takvim günü
`datetime.now(UTC).date()` ile alınıyordu; Türkiye'de 00:00–03:00 arasında bugünün tarihli
kalibrasyon kaydı "gelecek tarih" diye reddediliyor, izin bakiyesi, sözleşme ve vade hesapları bir
gün kayıyordu. Takvim günü artık `core.zaman.is_gunu()` (ayar `IS_SAAT_DILIMI`, varsayılan
`Europe/Istanbul`); zaman damgaları UTC kalır. Testler de aynı fonksiyonu kullanır.

## Sonuçlar

- Bildirim merkezi (S-VB), onay kutusu, içerik araması, code-split (S27-A) ile S27 kapandı.
  Kalan `uiplani.md` kalemleri (içe aktarma sihirbazı S21'de yapıldı; "Yenilikler" paneli,
  klavye kısayol haritası) kozmetik ve bilinçli olarak dışarıda.
- Lighthouse yerine axe-core: oturum gerektiren ekranlarda Lighthouse oturum açamıyor; axe aynı
  WCAG kurallarını oturumlu sayfada ölçüyor.
