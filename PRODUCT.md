# Product

## Register

product

## Users
İki birincil kullanıcı, tek üründe:
- **Saha/üretim operatörü ve vardiya amiri** — fabrika zemininde, çoğu zaman ayakta, büyük
  ekran veya tablet başında, hızlı bakıp aksiyon alır (makine durumu, OEE, iş emri, arıza).
  Dikkat süresi kısa; "tek bakışta durum" ister.
- **Tesis yöneticisi / planlamacı** — masada, çok modüllü ERP/MES verisini (üretim, bakım,
  stok, kalite) inceler; tablo, filtre, rapor yoğun ekranlarda çalışır.
Ortam çok-kiracılı SaaS: her fabrika kendi subdomain'inde, izole veriyle.

## Product Purpose
FabrikaOS, KOBİ üreticiler için çok-kiracılı bir MES+ERP platformudur: sahadan canlı üretim
verisini (OEE, makine durumu, arıza) toplar ve iş emri, bakım, stok, kalite gibi modülleri tek
çatı altında birleştirir. Başarı = operatör bir olayı saniyeler içinde görüp aksiyona dönüştürür;
yönetici dağınık tablolar yerine tek panodan tesisi yönetir.

## Brand Personality
**Üç kelime:** kontrollü, kesin, uyanık (controlled, precise, alert).
Ses: net ve teknik, abartısız. Bir kontrol odası panosu gibi — gürültü yok, sinyal var. Renk ve
hareket *bilgi taşır* (durum, uyarı, canlılık), dekorasyon değildir. Güven, "her şey gözümün
önünde ve elimde" hissinden gelir.

## Anti-references
- Genel "SaaS-cream/aydınlık-pastel" yönetim paneli görünümü — fabrika hissi vermez.
- Varsayılan, temasız Ant Design ("herkesin tanıdığı" şablon) — eşsiz değil.
- Tüketici uygulaması neşesi, yuvarlak-pastel kartlar, dekoratif gradyan/animasyon.
- Veriyi gömen düşük kontrast; kontrol odasında okunaksızlık kabul edilemez.

## Design Principles
1. **Tek bakışta durum.** En önemli sinyal (makine/OEE/uyarı) hiyerarşinin tepesinde, anında okunur.
2. **Renk ve hareket = bilgi.** Amber/cyan vurgu yalnızca durum/aksiyon için; sakin koyu zeminde sinyal öne çıkar.
3. **Yoğunluğa saygı.** Yönetici ekranları veri-yoğundur; tabloyu/sayıyı sıkıştırmaktan kaçınma, ama gürültüye boğma.
4. **Tutarlı dil, ekran-ekran.** Aynı buton, aynı form, aynı ikon dili her modülde. Sürpriz değil, güven.
5. **Erişilebilirlik pazarlık konusu değil.** Yüksek kontrast, klavye/odak, azaltılmış hareket — koyu temada bile.

## Accessibility & Inclusion
Hedef WCAG 2.1 AA. Gövde metni ≥4.5:1, büyük metin/sayısal vurgu ≥3:1 (koyu zeminde doğrulanır).
Tam klavye gezinmesi ve görünür odak halkası. `prefers-reduced-motion` için her geçişin sakin
alternatifi. Renk tek başına anlam taşımaz (durum ikonu/etiketi ile desteklenir) — renk körlüğü
için. Arayüz metinleri i18n (TR varsayılan, EN) ile çevrilebilir.
