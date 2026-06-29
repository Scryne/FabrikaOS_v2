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

## Typography
- **Gövde/UI:** `Inter Variable` (system-ui fallback). Tek aile; ürün UI'ı display/body
  eşleşmesine ihtiyaç duymaz.
- **Sayısal/veri:** `JetBrains Mono Variable` (`.sayisal` sınıfı, `tabular-nums`) — KPI,
  OEE, sayaç, kod, zaman hizalı okunur.
- **Ölçek:** sabit rem (akışkan değil), gövde 14px. Başlık `-0.02em` letter-spacing.

## Components (AntD token'ları)
`borderRadius` 10, kart `borderRadiusLG` 16, `wireframe:false`. Kabuk: bölümlü sol sidebar
(grup başlıkları + **mavi aktif pill** `itemSelectedBg` rgba(59,110,246,0.14) + alt tenant
kartı) + üst bar (arama + bildirim + dil + kullanıcı/rol). KPI kartı (büyük mono sayı +
renkli delta), donut/sütun grafikleri (hafif, bağımsız; gerçek ECharts S6'da), durum
nokta/pill'li tablolar. Her interaktif bileşen default→error tüm durumlarda.

## Motion
- 150–250 ms; hareket durum taşır (içerik açılışı, sütun büyümesi `transform: scaleY` ile —
  layout animasyonu değil). Easing ease-out; bounce yok. `prefers-reduced-motion` zorunlu.

## Layout
- Responsive yapısaldır: `lg` breakpoint'te sidebar çekmeceye çöker; KPI/grafik/tablo
  AntD Row/Col grid ile yeniden dizilir. Akışkan tipografi yok.
