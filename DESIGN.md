---
version: alpha
name: FabrikaOS
description: Çok kiracılı MES+ERP için koyu kontrol odası arayüzü — nötr antrasit zemin, mavi yalnızca vurgu, modül kimliği hat renkleriyle.
colors:
  zemin: "#0e0e0f"
  yuzey: "#161617"
  yuzey-2: "#0b0b0c"
  yuzey-ust: "#1d1d1f"
  kenarlik: "#262628"
  kenarlik-parlak: "#34343a"
  metin: "#f4f4f6"
  metin-soluk: "#8c8c92"
  mavi: "#3b6ef6"
  mavi-koyu: "#315fd6"
  cyan: "#38bdf8"
  basari: "#22c55e"
  uyari: "#f59e0b"
  hata: "#ef4444"
  mor: "#8b5cf6"
  hat-genel: "#3b6ef6"
  hat-uretim: "#38bdf8"
  hat-stok: "#2dd4bf"
  hat-kalite: "#8b5cf6"
  hat-isg-ik: "#f59e0b"
  hat-ticari: "#34d399"
  hat-dokuman: "#f472b6"
  hat-zeka: "#d946ef"
  hat-yonetim: "#94a3b8"
typography:
  govde:
    fontFamily: Inter Variable
    fontSize: 14px
  sayisal:
    fontFamily: JetBrains Mono Variable
    letterSpacing: 0.01em
  kpi-deger:
    fontFamily: JetBrains Mono Variable
    fontSize: 28px
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: -0.02em
rounded:
  borderRadius: 10px
  borderRadiusLG: 16px
components:
  kart:
    backgroundColor: "{colors.yuzey}"
    rounded: "{rounded.borderRadiusLG}"
    padding: 20px
  girdi:
    backgroundColor: "{colors.yuzey-ust}"
    rounded: "{rounded.borderRadius}"
    height: 38px
  buton:
    rounded: "{rounded.borderRadius}"
    height: 40px
  buton-birincil:
    backgroundColor: "{colors.mavi}"
    rounded: "{rounded.borderRadius}"
    height: 40px
  ust-bar:
    backgroundColor: "{colors.zemin}"
    height: 64px
  kenar-cubugu:
    backgroundColor: "{colors.yuzey-2}"
  menu-ogesi:
    textColor: "{colors.metin-soluk}"
    rounded: "{rounded.borderRadius}"
    height: 40px
---

## Overview

FabrikaOS, KOBİ üreticiler için çok kiracılı bir MES+ERP platformudur: saha operatörü bir
olayı saniyeler içinde görüp aksiyona dönüştürür, yönetici dağınık tablolar yerine tek
panodan tesisi yönetir. Görsel yön bir **kontrol odası panosu**: sakin, nötr koyu zemin;
renk ve hareket yalnızca durum ve aksiyon taşır, dekorasyon değildir. Kişilik: kontrollü,
kesin, uyanık. Yalnız koyu tema vardır — fabrika zemini ve uzun bakış için.

## Colors

- Zemin rampası **nötr antrasittir** (R=G=B); maviye/laciverte kaydırılmaz.
- `mavi` yalnızca aksiyon, aktif ve seçim içindir; yüzeyin küçük bir kısmını kaplar.
  Birincil buton, aktif menü ve odak halkası mavidir; başlık, kart veya zemin değildir.
- Semantik renkler (`basari`, `uyari`, `hata`, `cyan`) yalnız durum bildirir. Durum hiçbir
  zaman yalnız renkle anlatılmaz: nokta + etiket birlikte (`DurumPim`), renk körlüğü için.
- **Hat renkleri** endüstriyel hat/boru renk kodlaması metaforudur: her menü bölümünün bir
  hattı vardır. Kullanım yüzeyi bilinçli olarak küçüktür — sayfa başlığı ikon plakası, kenar
  çubuğu grup noktası, KPI ikon plakası, modül hat şeridi ve komut paletindeki satır noktası.
  Hat rengi kimlik sinyalidir; zemin veya büyük yüzey boyamak için kullanılmaz.
- Grafiklerde kategorik çok renk (mavi/yeşil/amber/mor/cyan) yalnızca veri serilerini ayırmak
  içindir.
- Kontrast hedefi WCAG 2.1 AA: gövde metni ve `metin-soluk` koyu zemin üzerinde AA geçer;
  birincil butonda metin beyazdır.

## Typography

- Tek UI ailesi `govde` (Inter); ürün arayüzü display/body eşleşmesine ihtiyaç duymaz.
- Her sayısal değer — KPI, OEE, sayaç, kod, zaman — `sayisal` ölçeğiyle ve tabular rakamla
  yazılır ki sütunlarda hizalı okunsun. Büyük göstergeler `kpi-deger` ölçeğini kullanır.
- Ölçek sabittir (akışkan tipografi yok); tek istisna kiosk büyük ekranının KPI değeridir.

## Layout

- Kabuk: bölümlü sol kenar çubuğu (hat noktalı grup başlıkları, aktif öğe mavi hap, altta
  tenant/çalışma alanı kartı) + üst bar (komut paleti tetiği, saat, canlı bağlantı rozeti, dil,
  bildirim, kullanıcı/rol çipi) + içerik.
- `lg` altında kenar çubuğu çekmeceye çöker ve içeriğin üstüne katman olarak açılır; tetiği
  üst barın içindedir. Dar ekranda üst bar yalnız işlev taşır (saat, ayraç, kullanıcı adı ve
  kısayol ipucu gizlenir); sayfa hiçbir genişlikte yatay kaymaz.
- Her modül ekranı aynı iskeleti izler: `SayfaKapsayici` (üstte modül hat şeridi) →
  `SayfaBaslik` (hat renkli ikon plakası + bölüm kırıntısı + başlık + alt metin + sağ aksiyon)
  → `OzetSerit` (3-4 KPI, modülün `/ozet` ucundan) → `GorunumGecis` (Liste / Pano / Analiz;
  pano yalnız durum odaklı modüllerde) → içerik.
- KPI, grafik ve tablo AntD Row/Col ızgarasıyla yeniden dizilir; pano mozaiği görünür
  genişliğe göre sütun sayısı seçer.

## Elevation & Depth

- Koyu zeminde derinlik gölgeyle değil ışık kenarıyla kurulur: kartlar ince düşük kontrastlı
  `kenarlik` taşır, `PanelKart` üstte iç ışık çizgisi taşır.
- Yalnızca açılır katmanlar (dropdown, popover, modal, tooltip) karartı gölgesi + 1px ışık
  halkası alır.

## Shapes

- Kontroller `borderRadius`, kartlar ve paneller daha yumuşak `borderRadiusLG` kullanır.

## Components

- **Tek kelime hazinesi, ekran-ekran aynı.** Yeni ekran önce paylaşılan primitiflerden kurulur:
  `OzetSerit`/`KpiKart`, `PanelKart`, `DurumPim`, `MiniBar`, `KanbanPano`/`VeriKart`,
  `RiskMatrisi`, `UyariKarti`, `AktiviteAkisi`, `KomutPaleti`, varlık hücresi, `BosDurum`.
  Modül-yerel alternatif yazılmaz.
- Durum gösterimi AntD `Tag` yerine `DurumPim` ile yapılır; dijital ikiz ve kiosk LED'leri aynı
  durum sözlüğünü kullanır.
- Uyarılar önem renginde hafif tint + eş renk yumuşak kenar + renkli ikon taşır (yan şerit değil).
- Tablolar `SunucuTablo` üzerinden gelir: kayıt sayacı çipi + arama + filtre araç çubuğu; boş
  durum `BosDurum` ile ne yapılacağını öğretir (ikon + başlık + açıklama + isteğe bağlı CTA).
- Grafikler `grafikSecenek` üreticilerinden gelir (tema renkleri, koyu ipucu, kategori ekseninde
  sığmayan etiketler otomatik seyreltilir; tam ad ipucundadır).
- Giriş ekranının imzası sol marka panelindeki animasyonlu üretim hattı şemasıdır.
- Her etkileşimli bileşen varsayılandan hataya tüm durumları taşır; odak halkası her zaman
  görünürdür.

## Do's and Don'ts

- Do: hareketi yalnız durum için kullan (içerik açılışı, sütun büyümesi); `transform` ile anime
  et, layout özelliğini anime etme. Easing ease-out; sıçrama yok.
- Do: her geçişin `prefers-reduced-motion` altında sakin bir karşılığı olsun.
- Don't: genel "SaaS-cream/aydınlık pastel" panel görünümü, temasız varsayılan Ant Design,
  tüketici uygulaması neşesi, dekoratif gradyan veya animasyon.
- Don't: veriyi gömen düşük kontrast; kontrol odasında okunaksızlık kabul edilemez.
