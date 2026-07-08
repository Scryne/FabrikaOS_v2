# Design

Görsel sistem: **premium dark SaaS** — **nötr antrasit** zemin (R=G=B, lacivert değil), **mavi
YALNIZCA vurgu** (aksiyon/aktif/seçim), yumuşak büyük yuvarlak kartlar, ince düşük-kontrast
kenarlık, Inter tipografi, sayısal değerlerde JetBrains Mono. Zemin rampası referansı: koyu
kontrol-odası panoları (#101010/#181818 ailesi, mükemmel nötr gri). Ant Design v5 motor; bu
token'lar onun üstüne giydirilen "deri"dir. Tek doğruluk kaynağı: `frontend/src/tema/tema.ts`
(AntD token'ları) + `frontend/src/index.css` (CSS değişkenleri).

## Theme
- **Mod:** yalnızca koyu. Senaryo: fabrika/kontrol odası + masabaşı yönetim; koyu zemin canlı
  veriyi öne çıkarır, uzun bakışta yormaz.
- **Color strategy:** Restrained — sakin koyu nötr yüzeyler + tek mavi vurgu (yüzeyin <%10'u)
  yalnızca aksiyon/aktif/seçim için. Renk = sinyal, dekorasyon değil. Grafiklerde kategorik
  çok-renk (mavi/yeşil/amber/mor) yalnızca veri serilerini ayırmak için.

## Color
Nötr antrasit rampa (R=G=B; lacivert/mavi kayması YOK) + mavi vurgu + semantik durumlar
(AntD hex bekler; CSS değişkeni olarak da açılır).

| Rol | Token | Değer |
|---|---|---|
| Zemin | `--zemin` | `#0e0e0f` |
| Yüzey (kart) | `--yuzey` | `#161617` |
| Yüzey-2 (sidebar) | `--yuzey-2` | `#0b0b0c` |
| Yüzey-üst (input/elevated) | `--yuzey-ust` | `#1d1d1f` |
| Kenarlık | `--kenarlik` | `#262628` (düşük kontrast, yumuşak) |
| Metin | `--metin` | `#f4f4f6` (≥4.5:1) |
| Metin-soluk | `--metin-soluk` | `#8c8c92` (~5.6:1) |
| Birincil (mavi) | `colorPrimary` | `#3b6ef6` — aksiyon/aktif/seçim |
| Info (cyan) | `colorInfo` | `#38bdf8` |
| Başarı | `colorSuccess` | `#22c55e` |
| Uyarı | `colorWarning` | `#f59e0b` |
| Hata | `colorError` | `#ef4444` |
| Ek (mor, data-viz) | `--mor` | `#8b5cf6` |

Durum-zengin semantik (default/hover/focus/active/disabled/selected/loading/error).
Mavi buton üzerinde beyaz metin AA geçer (~4.8:1). Durum göstergeleri renk + nokta/etiket
(renk körlüğü için renk tek başına anlam taşımaz).

### Hat renkleri (modül kimliği)
Endüstriyel hat/boru renk kodlaması metaforu: her menü bölümü bir **hat rengi** taşır.
Kullanım yüzeyi bilinçli olarak küçüktür (~%2-3): sayfa başlığı ikon plakası, sidebar grup
noktası, KPI ikon plakası. Restrained strateji bozulmaz — renk kimlik sinyalidir, dekor değil.
Tek doğruluk kaynağı: `frontend/src/tema/modulKimlik.tsx` (+ `--hat-*` CSS değişkenleri).

| Bölüm | Token | Değer |
|---|---|---|
| Genel | `--hat-genel` | `#3b6ef6` |
| Üretim | `--hat-uretim` | `#38bdf8` |
| Stok & Satınalma | `--hat-stok` | `#2dd4bf` |
| Kalite & Enerji | `--hat-kalite` | `#8b5cf6` |
| İSG & İK | `--hat-isg-ik` | `#f59e0b` |
| Ticari | `--hat-ticari` | `#34d399` |
| Doküman & Duyuru | `--hat-dokuman` | `#f472b6` |
| Zekâ | `--hat-zeka` | `#d946ef` |
| Yönetim | `--hat-yonetim` | `#94a3b8` |

## Typography
- **Gövde/UI:** `Inter Variable` (system-ui fallback). Tek aile; ürün UI'ı display/body
  eşleşmesine ihtiyaç duymaz.
- **Sayısal/veri:** `JetBrains Mono Variable` (`.sayisal` sınıfı, `tabular-nums`) — KPI,
  OEE, sayaç, kod, zaman hizalı okunur.
- **Ölçek:** sabit rem (akışkan değil), gövde 14px. Başlık `-0.02em` letter-spacing.

## Components (AntD token'ları)
`borderRadius` 10, kart `borderRadiusLG` 16, `wireframe:false`. Kabuk: bölümlü sol sidebar
(hat noktalı grup başlıkları + tüm modüllerde ikon + **mavi aktif pill** `itemSelectedBg`
rgba(59,110,246,0.14) + alt tenant/çalışma alanı kartı) + üst bar (arama + saat + **canlı
rozet** (gerçek-zaman WS durumu) + dil + bildirim + kullanıcı/rol çipi). Açılır katmanlar
(dropdown/modal/tooltip) karartı + 1px ışık halkası gölgesi taşır (`boxShadowSecondary`).

Ekran desenleri (tek kelime hazinesi, ekran-ekran aynı):
- **SayfaBaslik** — rotadan otomatik modül kimliği: hat renkli ikon plakası (`.ikon-plaka`) +
  bölüm kırıntısı (hat noktası + bölüm adı) + başlık + alt metin + sağ aksiyon.
- **SunucuTablo** — araç çubuğu (kayıt sayacı çipi `.kayit-sayaci` + arama + filtre) + tablo;
  boş durumlar **BosDurum** (ikon + başlık + açıklama + opsiyonel CTA) ile öğretir.
- **KpiKart** — büyük mono sayı (`.kpi-deger` 28px) + hat renkli küçük ikon plakası + delta.
- **Kanban kartı** (`.kanban-kart`) — hover'da hafif kalkış (transform+gölge); kolon başlığında
  durum noktası + sayaç.
- **Giriş ekranı imzası** — sol marka panelinde animasyonlu üretim hattı şeması (`.giris-hat`,
  akan cyan sinyal; reduced-motion'da statik soluk çizgi).
Her interaktif bileşen default→error tüm durumlarda.

## Motion
- 150–250 ms; hareket durum taşır (içerik açılışı, sütun büyümesi `transform: scaleY` ile —
  layout animasyonu değil). Easing ease-out; bounce yok. `prefers-reduced-motion` zorunlu.

## Layout
- Responsive yapısaldır: `lg` breakpoint'te sidebar çekmeceye çöker; KPI/grafik/tablo
  AntD Row/Col grid ile yeniden dizilir. Akışkan tipografi yok.
