# Design

Görsel sistem: **endüstriyel kontrol odası** — koyu (dark-only), yüksek kontrast, amber/cyan
sinyal vurgusu, sayısal değerlerde monospace. Ant Design v5 motor; bu token'lar onun üstüne
giydirilen "deri"dir (ConfigProvider + CSS değişkenleri). Tek doğruluk kaynağı: `src/tema/tema.ts`
(AntD token'ları) + `src/index.css` (CSS değişkenleri).

## Theme
- **Mod:** yalnızca koyu (light yok). Senaryo: fabrika zemini/kontrol odası, değişken ortam
  ışığı, çoğu zaman büyük ekran; koyu zemin parlamayı azaltır ve canlı veriyi öne çıkarır.
- **Color strategy:** Restrained — sakin koyu nötr yüzeyler + amber birincil ve cyan info
  yalnızca durum/aksiyon için (yüzeyin <%10'u). Vurgu = sinyal, dekorasyon değil.

## Color
Koyu slate nötr rampa + iki sinyal vurgu + semantik durumlar. (AntD renk algoritması hex bekler;
değerler hex tutulur, CSS değişkenleri olarak da açılır.)

| Rol | Token | Değer | Not |
|---|---|---|---|
| Zemin | `--zemin` | `#0B0F14` | en koyu slate, app arka planı |
| Yüzey | `--yuzey` | `#131A24` | kart/panel |
| Yüzey-2 | `--yuzey-2` | `#1A2330` | kenar çubuğu/araç çubuğu (ikinci nötr katman) |
| Kenarlık | `--kenarlik` | `#26303F` | ince ayraçlar |
| Metin | `--metin` | `#E6EDF3` | gövde, yüksek kontrast (≥4.5:1) |
| Metin-soluk | `--metin-soluk` | `#94A3B8` | ikincil; AA gövde sınırında, etiketler için |
| Birincil (amber) | `colorPrimary` | `#F5A524` | aksiyon, aktif, marka sinyali |
| Info (cyan) | `colorInfo` | `#22D3EE` | seçim, bağlantı, canlı/info |
| Başarı | `colorSuccess` | `#10B981` | çalışıyor/onaylı |
| Uyarı | `colorWarning` | `#FB923C` | dikkat (amberden ayrı, daha turuncu) |
| Hata | `colorError` | `#EF4444` | arıza/hata |

Durum-zengin semantik (her interaktif öğede): default/hover/focus/active/disabled/selected/
loading/error. Vurgu yalnız birincil aksiyon, geçerli seçim, durum göstergesinde; pasif
durumlarda tam-doygunluk yok.

## Typography
- **Gövde/UI:** tek aile, sistem sans yığını: `system-ui, 'Segoe UI', Roboto, ...`. Ürün UI'ı
  display/body eşleşmesine ihtiyaç duymaz.
- **Sayısal/veri:** monospace yığını (`ui-monospace, 'Cascadia Code', 'Consolas', monospace`),
  `.sayisal` sınıfı / AntD `Statistic`. OEE, sayaç, kod, zaman damgası hizalı okunur.
- **Ölçek:** sabit rem (akışkan değil), 1.2 oran. Gövde 14px (AntD varsayılanı), yoğun UI'a uygun.
- Prose satır uzunluğu 65–75ch; tablolar daha yoğun olabilir.

## Components
AntD v5 bileşenleri + koyu tema token'ları. `borderRadius` 6px (sıkı, teknik), `wireframe:false`.
Her interaktif bileşen: default/hover/focus/active/disabled/loading/error. Yükleme için skeleton,
içerik ortasında spinner değil. Boş durumlar arayüzü öğretir. App kabuğu: sol kenar çubuğu (RBAC
menü) + üst bar (tenant/kullanıcı/dil/çıkış); kabuk `--yuzey-2` ikinci nötr katmanda.

## Motion
- 150–250 ms; kullanıcı akışta, koreografi bekletmez. Hareket durum taşır (durum değişimi,
  geri bildirim, yükleme, açılış), dekorasyon değil. Sayfa-yükü koreografisi yok.
- Easing: ease-out (expo/quart); bounce/elastic yok.
- `prefers-reduced-motion: reduce` → anında/çapraz geçiş alternatifi (zorunlu).

## Layout
- Responsive yapısaldır: kenar çubuğu daraltma/çekmece, responsive tablo, breakpoint sütunları —
  akışkan tipografi değil.
- Z-index semantik ölçek: dropdown → sticky → modal-backdrop → modal → toast → tooltip.
