# FabrikaOS — UI/UX Master Planı (v2)

> **Sürüm 2 · 2026-07-08.** Kapsam: mevcut tüm ekranlar (Faz 0–3, 9 menü bölümü / ~31 rota)
> **+ henüz yapılmamış fazların (Faz 4–6) UI planı**. Bu belge ürünün arayüz tarafındaki
> **tek doğruluk kaynağıdır**; yol haritasındaki S27 (Platform Deneyimi) bu planın kalan
> kalemlerinin tamamlandığı sprinttir. Görsel token/desen doğruluk kaynağı `DESIGN.md`'dir;
> bu plan onun *uygulama haritasıdır*.

## v1'den farklar (değişiklik günlüğü)

- v1, Faz 3 öncesi yazılmıştı. **Zekâ bölümü** (AI Tahminleri, Analitik, Raporlar),
  **Dijital İkiz** (`/ikiz`) ve **Kiosk** (`/kiosk`) eklendi; hat rengi sayısı 8 → **9**
  (Zekâ `#d946ef` fuşya — `modulKimlik.tsx`'te zaten vardı; `DESIGN.md` hat renkleri
  tablosuna satırı bu planla birlikte eklendi).
- **Bölüm 3 (bilgi mimarisi)** eklendi: mevcut + gelecek tüm rotaların tek haritası.
- **Bölüm 7 (modül çalışma alanları)** her modül için ekran-ekran derinleştirildi:
  KPI şeridi metrikleri, tablo kolonları + satır-içi görselleştirme, board kolonları,
  analiz grafikleri, detay profili, boş durum — hepsi tek tek yazıldı.
- **Bölüm 11 (gelecek fazların UI planı)** eklendi: Faz 4 (Abonelik/Platform Admin/Dış
  Portal), Faz 5 (sistem sağlığı, onboarding sihirbazı) ve Faz 6 (kurumsal derinleşme —
  yol haritası S23–S28 ile birebir hizalı) ekranları.

---

## 1. Context (neden?)

Ürün tek koyu AntD kabuğu (`UygulamaKabugu`) içinde ~31 rotadan oluşuyor ve liste
ekranlarının neredeyse tamamı **aynı iskelete** indirgeniyor: `SayfaBaslik` + `Card` +
`SunucuTablo`. Yani her sayfa "başlık + tek bir tablo". Bu, işlevsel ama **tekdüze**
bir görünüm veriyor; veri zengin olduğu hâlde tek boyutlu liste olarak sunuluyor. Tasarım
sistemi aslında iyi kurulmuş (nötr antrasit tema + 9 modül "hat rengi" kimliği + ECharts
sarmalayıcı + kiosk/ikiz gibi imza ekranlar), ama bu güç pano/ikiz/kiosk dışında hiçbir
sayfada kullanılmıyor.

**Hedef:** mevcut **"kontrol odası" felsefesini bozmadan evrimleştirerek** her modül
ekranını tek-tabloluktan çıkarıp; özet/KPI şeridi + zengin tablo + (durum-odaklı
modüllerde) board görünümü + grafik/analiz + zengin detay profillerinden oluşan
**profesyonel, tutarlı ve eşsiz** bir "modül çalışma alanına" dönüştürmek — ve bu dili
gelecek fazların ekranlarına (entitlement, platform admin, dış portal, kurumsal
derinleşme) baştan taşımak. Renk hâlâ sinyal (DESIGN.md korunur ve genişletilir),
zenginlik düzen + veri-görselleştirme + hat rengi kimlikten gelir.

**Onaylanan kararlar:** görsel yön = *Kontrol Odası (Evrim)*; kapsam = *tüm ekranlar*;
KPI verisi = *modül başına küçük salt-okunur `/ozet` uçları*; *durum-odaklı modüllere
liste↔board (Kanban) görünümü*.

Tasarım işinde `impeccable` / `frontend-design` skill ilkeleri; backend `/ozet` uçlarında
`tenant-rbac-conventions` + `turkce-identifier-standardi` esas alınır (şema değişmez →
migration yok; sorgular `search_path`/tenant-izole).

---

## 2. Tasarım dili — "Kontrol Odası (Evrim)"

Mevcut token sistemi (nötr antrasit `#0e0e0f`/`#161617`, mavi=YALNIZ vurgu, 9 hat rengi)
**korunur**. Üstüne şu görsel imzalar eklenir (hepsi "renk=sinyal, ~%2-3 yüzey" kuralına sadık):

- **Hat şeridi (page rail):** her sayfa başlığının üstünde modül hat renginde ince yatay
  degrade hairline — sayfanın hangi modülde olduğunu anında söyler.
- **Enstrüman-panel kartları:** kart üstünde 1px iç ışık çizgisi, başlıkta hat renkli minik
  aksan; sayısal her değer JetBrains Mono (`.sayisal`).
- **Durum LED'leri:** her yerde nokta+etiket "pim" (renk körlüğü güvenli), Tag yerine
  tutarlı `DurumPim`. İkiz/kiosk'taki LED dili liste ekranlarıyla aynı sözlüğü konuşur.
- **Satır içi veri-görselleştirme:** tablolarda mini oran barı (OEE, stok/kritik), mini
  sparkline (trend), durum pimi — "tablo ama okunur pano gibi".
- **Sakin hareket (korunur):** içerik açılışı, sütun `scaleY` büyümesi, kart hover kalkışı;
  KPI sayaç animasyonu opsiyonel — `prefers-reduced-motion` zorunlu.
- **Komut paleti (⌘K):** üst bar araması gerçek bir global gezinme paletine dönüşür;
  Faz 6/S27'de içerik aramayla derinleşir (bkz. §11.3).
- **Alt-diller:** *Kiosk* = uzak-okuma tipografisi (KPI 48–64px, 0 interaksiyon);
  *İkiz* = şema dili (ince ızgara zemin, bölge çerçeveleri, LED + OEE bar);
  *Dış Portal* (Faz 4) = aynı antrasit ailenin sadeleştirilmiş tek-modül kabuğu;
  *Platform Admin* (Faz 4) = aynı token, ayrı "platform" kimlik rengi (bkz. §11.1).

`DESIGN.md` bu desenlerle (OzetSerit, GorunumGecis, KanbanPano, PanelKart, komut paleti,
satır-içi dataviz) güncellenir (**Zekâ hat rengi satırı eklendi**); tek doğruluk kaynağı kalır.

---

## 3. Bilgi mimarisi — tam site haritası

Menü bölümü → hat rengi → rotalar. Durum: ✅ mevcut · 🔜F4/F5/F6 planlı (ilgili faz).

| Bölüm (hat rengi) | Rota | Ekran | İzin | Durum |
|---|---|---|---|---|
| **Genel** `#3b6ef6` | `/` | 360° Yönetim Panosu | (oturum) | ✅ |
| **Üretim** `#38bdf8` | `/makineler` (+`/:id`) | Makineler + Makine Detay | `uretim:oku` | ✅ |
| | `/uretim-verileri` | Üretim Verileri | `uretim:oku` | ✅ |
| | `/is-emirleri` | İş Emirleri (liste+kanban) | `isemri:oku` | ✅ |
| | `/ikiz` | Dijital İkiz (SVG şema) | `uretim:oku` | ✅ |
| | `/saha/cihazlar` | Saha Cihazları | `saha:oku` | ✅ |
| | `/bakim-planlari` | Bakım Planları | `bakim:oku` | ✅ |
| | `/vardiyalar`, `/durus-kayitlari` | Vardiya & Duruş yönetimi | `uretim:*` | 🔜F6·S24 |
| | `/urunler` | Ürün & Reçete (BOM) | `uretim:*` | 🔜F6·S24 |
| | `/izlenebilirlik` | Lot ileri/geri izleme | `uretim:oku` | 🔜F6·S24 |
| **Stok & Satınalma** `#2dd4bf` | `/malzemeler` (+`/:id`) | Malzemeler + Detay | `stok:oku` | ✅ |
| | `/stok/kritik` | Kritik Stok | `stok:oku` | ✅ |
| | `/satinalma-talepleri` | Satınalma Talepleri | `satinalma:oku` | ✅ |
| | `/depolar`, `/sayimlar` | Depo/Lokasyon + Sayım | `stok:*` | 🔜F6·S25 |
| | `/satinalma-siparisleri` | Satınalma Siparişleri (PO) | `satinalma:*` | 🔜F6·S25 |
| **Kalite & Enerji** `#8b5cf6` | `/kalite-kontrolleri` | Kalite Kontrolleri | `kalite:oku` | ✅ |
| | `/uygunsuzluklar` | Uygunsuzluklar (CAPA) | `kalite:oku` | ✅ |
| | `/enerji-tuketimleri` | Enerji | `enerji:oku` | ✅ |
| | `/kontrol-planlari`, `/spc` | Kontrol Planları + SPC | `kalite:*` | 🔜F6·S26 |
| | `/kalibrasyonlar` | Ölçüm cihazı & kalibrasyon | `kalite:*` | 🔜F6·S26 |
| **İSG & İK** `#f59e0b` | `/is-kazalari` | İş Kazaları | `isg:oku` | ✅ |
| | `/risk-degerlendirmeleri` | Risk Değerlendirmeleri | `isg:oku` | ✅ |
| | `/personeller` (+`/:id`) | Personeller + Detay | `ik:oku` | ✅ |
| | `/izin-talepleri` | İzin Talepleri | `ik:oku` | ✅ |
| | `/isg-egitimleri`, `/org-semasi` | İSG eğitim + Org şeması | `isg`/`ik` | 🔜F6·S26 |
| **Ticari** `#34d399` | `/ticari` | Ticari Pano | `crm:oku` | ✅ |
| | `/firmalar` | Firmalar (CRM) | `crm:oku` | ✅ |
| | `/sozlesmeler` | Sözleşmeler | `crm:oku` | ✅ |
| | `/talepler` | Talepler | `crm:oku` | ✅ |
| **Doküman & Duyuru** `#f472b6` | `/belgeler` | Belgeler (DYS) | `dys:oku` | ✅ |
| | `/duyurular` | Duyurular | (oturum) | ✅ |
| **Zekâ** `#d946ef` | `/tahminler` | AI Tahminleri | `ai:oku` | ✅ |
| | `/analitik` | Analitik Pano | `analitik:oku` | ✅ |
| | `/raporlar` | Raporlar | `rapor:oku` | ✅ |
| **Yönetim** `#94a3b8` | `/kullanicilar` | Kullanıcılar | `kullanici:oku` | ✅ |
| | `/abonelik` | Abonelik & Modüller | admin | 🔜F4·S16 |
| | `/webhooklar` | Webhook yönetimi | admin | 🔜F4·S18 |
| | `/sistem-sagligi` | Sistem Sağlığı | admin | 🔜F5·S19 |
| | `/denetim-kayitlari` | Denetim Kaydı görüntüleyici | admin | 🔜F6·S23 |
| | `/bildirim-tercihleri`, `/oturumlar` | Bildirim tercihleri + Oturumlar | (oturum) | 🔜F6·S23/S27 |
| | `/onaylarim` | Birleşik Onay Kutusu | rol-duyarlı | 🔜F6·S27 |
| **Kabuksuz** | `/giris` | Giriş (marka paneli) | — | ✅ |
| | `/kiosk` | Kiosk büyük ekran | `kiosk` rolü | ✅ |
| | `/onizleme` | Tasarım önizleme (yalnız DEV) | — | ✅ |
| **Ayrı SPA'lar** | `platform.*` | Platform Admin Paneli | `platform-admin` | 🔜F4·S17 |
| | `portal.*` / `/dis` | Dış Self-Servis Portal | `dis-panel` | 🔜F4·S18 |

---

## 4. Katman 1 — Temel (token + primitifler)

**Dokunulan / genişletilen çekirdek dosyalar:**
- `frontend/src/index.css` — yeni yardımcı sınıflar: `.hat-serit` (page rail degrade),
  `.panel-kart` (iç ışık çizgisi), `.mini-bar`/`.mini-bar-dolu`, `.durum-pim`, `.ozet-serit`,
  `.gorunum-gecis`, `.komut-paleti`, gelişmiş `.bos-durum` ve skeleton hijyeni.
- `frontend/src/tema/tema.ts` — küçük rafinasyonlar (List/Timeline/Descriptions/Progress/
  Badge override'ları; kart hover, tablo satır tıklama imleci). Renk rampası değişmez.
- `frontend/src/tema/modulKimlik.tsx` — gerektikçe yeni menü ikonları; API aynı.
- `frontend/src/components/grafik/grafikSecenek.ts` — yeni saf üreticiler: `alanSecenek`
  (gradient dolgulu alan/çizgi), `yiginCubukSecenek`, `isiHaritaSecenek`, `sparklineSecenek`,
  `paretoSecenek` (kalite/duruş), `kontrolGrafikSecenek` (SPC, F6). Hepsi birim testli
  (mevcut `grafikSecenek.test.ts` desenine ekleme).

**Paylaşılan primitifler (`frontend/src/components/`):**

| Bileşen | Görev | Kullanım | Evre |
|---|---|---|---|
| `OzetSerit.tsx` | Modül üstü KPI/özet şeridi (3-4 metrik, hat rengi, responsive) | Tüm liste ekranları | şimdi |
| `KpiKart.tsx` (genişlet) | Opsiyonel `seri?: number[]` → satır içi `MiniTrend` | KPI şeritleri, panolar | şimdi |
| `MiniTrend.tsx` | Küçük sparkline (SVG/ECharts) | KpiKart, tablo hücreleri | şimdi |
| `MiniBar.tsx` | Satır içi oran barı (değer/eşik, semantik renk) | Tablolar (OEE, stok, risk) | şimdi |
| `DurumPim.tsx` | Birleşik durum pimi (nokta+etiket); `pimUret(harita)` | Tüm `rozetler.tsx` | şimdi |
| `PanelKart.tsx` | Başlıklı "enstrüman panel" kart (hat aksanlı üst çizgi + extra slot) | Panolar, detay, analiz | şimdi |
| `GorunumGecis.tsx` | Liste / Board / Analiz `Segmented` geçişi (rota state'e bağlı) | Durum-odaklı modüller | şimdi |
| `FiltreCubugu.tsx` | Tutarlı filtre çubuğu (arama + segmented + select'ler) | Liste + board üstü | şimdi |
| `KanbanPano.tsx` | Genelleştirilmiş kanban (kolonlar=durumlar, `kartCiz`, geçiş) — `IsEmriKanban`'dan soyutlanır | Tüm board görünümleri | şimdi |
| `VeriKart.tsx` | Board/grid varlık kartı (başlık, alt, meta çipleri, durum, footer) | Kanban kartları, belge grid | şimdi |
| `AktiviteAkisi.tsx` | Zaman çizelgesi/aktivite akışı (renkli ikon + başlık + zaman) | Panolar, detaylar | şimdi |
| `UyariKarti.tsx` | Önem-renkli uyarı kartı (kritik/uyarı/bilgi) | Kalite/İSG/Bakım/Stok | şimdi |
| `SayfaKapsayici.tsx` | `maxWidth:1320` + hat şeridi standart sarmalayıcı | Tüm sayfalar | şimdi |
| `KomutPaleti.tsx` | ⌘K global gezinme paleti (menüden beslenir, RBAC filtreli) | Kabuk | şimdi |
| `RiskMatrisi.tsx` | 5×5 olasılık×şiddet ısı görseli (hücrede sayaç, tıkla→filtre) | İSG Risk | şimdi |
| `TakvimZaman.tsx` | Takvim / zaman çizelgesi görünümü | Bakım, vardiya (F6), kalibrasyon (F6) | şimdi/F6 |
| `AdimSihirbaz.tsx` | Çok adımlı sihirbaz (Steps + doğrulamalı ilerleme) | Onboarding (F5), provizyon (F4), 2FA (F6) | F4/F5 |
| `AgacGorunum.tsx` | Hiyerarşi ağacı (düzenlenebilir) | BOM, depo/lokasyon, org şeması | F6 |
| `BildirimPaneli.tsx` | Zil → gerçek bildirim listesi (okundu, tercih linki) | Kabuk üst bar | F6·S27 |
| `DisaAktarMenu.tsx` | CSV/XLSX dışa aktarma menüsü (async 202 farkındalıklı) | Tüm liste ekranları | F6·S27 |

`SunucuTablo.tsx` genişletilir: opsiyonel `filtreler` slotu, satır `⋯` aksiyon menüsü,
hücre yardımcıları (varlık hücresi: ikon/avatar + ad + alt metin). API geriye uyumlu kalır.

---

## 5. Katman 2 — Kabuk & gezinme (`UygulamaKabugu.tsx`)

- **Sidebar:** hat-noktalı grup başlıkları korunur; daralabilir "rail" modu (ikon-only),
  aktif pill rafine, tenant kartı cilalanır. F4·S16'dan itibaren menü **entitlement**
  süzgeçli (kapalı modül menüde görünmez; bkz. §11.1).
- **Üst bar:** arama kutusu → `KomutPaleti` tetikleyicisi (⌘K etiketiyle); `canli-rozet`
  rafine; bildirim zili → önce duyuru/uyarı akışı `Dropdown`'ı, F6·S27'de gerçek
  `BildirimPaneli`; breadcrumb bağlamı; kullanıcı menüsüne "Oturumlarım" (F6·S23) ve
  "Bildirim tercihleri" (F6·S27) girişleri.
- **İçerik:** `SayfaKapsayici` + hat şeridi; mevcut `icerik-acilis` animasyonu korunur.

---

## 6. Katman 3 — Modül çalışma alanı deseni (ortak iskelet)

Her liste ekranı şu tutarlı iskelete geçer (desen bir kez tanımlanır, ~22 ekrana uygulanır):

```
SayfaKapsayici
 ├─ hat şeridi (modül rengi)
 ├─ SayfaBaslik  (breadcrumb + ikon plaka + başlık + alt + birincil aksiyon + "güncellendi" çipi)
 ├─ OzetSerit    (use<Modul>Ozet() → 3-4 KPI: durum sayıları, kritik/açık toplamları, trend)
 ├─ GorunumGecis (Liste / Board / Analiz)   ← board yalnız durum-odaklı modüllerde
 │    ├─ Liste  : PanelKart > FiltreCubugu + zengin SunucuTablo (DurumPim, MiniBar, varlık hücresi, ⋯)
 │    ├─ Board  : KanbanPano (VeriKart'lar + durum makinesi geçişleri)
 │    └─ Analiz : PanelKart'lar içinde EGrafik'ler (modüle özel)
 └─ Drawer/Modal formlar (mantık aynı, yalnız restyle)
```

Boş durumlar her ekranda **öğretir**: ikon + başlık + bir cümle açıklama + CTA (ilgili
oluşturma aksiyonu; F5·S21 sonrası onboarding sihirbazına bağlanır).

---

## 7. Modül çalışma alanları — ekran-ekran detay

### 7.1 Genel — 360° Yönetim Panosu `/` (mavi `#3b6ef6`)

- **Amaç:** Fabrikanın tek bakışta sağlığı; yöneticinin güne başladığı ekran.
- **KPI şeridi:** dönem OEE (mini trend'li) · çalışan/toplam makine · açık iş emri ·
  kritik stok kalemi · açık uygunsuzluk · bugünkü üretim adedi.
- **Gövde:** OEE gauge + makine durum donut (korunur) · **üretim trend alan grafiği**
  (7/30 gün) · **gerçek-zaman uyarı şeridi** (`UyariKarti`: kritik stok, anomali,
  yaklaşan sözleşme, SPC ihlali F6) · makine durum kartları · enerji mini özeti ·
  son üretim tablosu · `AktiviteAkisi` (son olaylar: isemri.durum, kalite.uygunsuzluk...).
- Hem `PanoSayfasi` hem `OnizlemePano` aynı sunum bileşenini (`PanoIcerik`) besler.

### 7.2 Üretim (cyan `#38bdf8`)

**Makineler `/makineler`**
- KPI: toplam makine · çalışıyor · arızada/bakımda · ortalama OEE (mini trend).
- Liste: varlık hücresi (ikon + ad + kod) · `DurumPim` (çalışıyor/durdu/arızada/bakımda) ·
  OEE `MiniBar` (eşik renkli: ≥85 yeşil, 60–85 amber, <60 kırmızı) · son veri zamanı ·
  `⋯` (durum değiştir, detay, ikizde göster).
- Analiz: durum donut · OEE dağılım çubuğu · vardiya kırılımı (F6·S24 sonrası).
- Boş durum: "Henüz makine yok — ilk makinenizi ekleyin" + CTA.

**Makine Detay `/makineler/:id`** — profil düzeni: kimlik başlığı (ad, kod, `DurumPim`,
durum değiştir aksiyonu) · OEE gauge + Kullanılabilirlik/Performans/Kalite bileşen barları ·
üretim trend alan grafiği · son üretim verileri · arıza/bakım `AktiviteAkisi` · ikiz
konumu mini haritası (yerleşmişse "ikizde gör" bağlantısı).

**Üretim Verileri `/uretim-verileri`**
- KPI: bugünkü üretim · fire adedi/oranı · aktif veri kaynağı kırılımı (manuel/saha) ·
  son 24 saat kayıt sayısı.
- Liste: makine varlık hücresi · miktar/fire (mono) · kaynak çipi (manuel/MQTT/CSV) · zaman.
- Analiz: günlük trend alan grafiği · saatlik **ısı haritası** · makine bazlı yığın çubuk.
- Form (giriş): makine + miktar + fire + süre; doğrulama hataları alan-altı.

**İş Emirleri `/is-emirleri`**
- KPI: açık · devam eden · bugün kapanan · ortalama kapanış süresi.
- **Liste↔Board:** mevcut `IsEmriKanban` genelleştirilmiş `KanbanPano`'ya taşınır
  (kolonlar: açık → atandı → devam ediyor → kapandı; iptal ayrı süzgeç). `VeriKart`:
  `IE-` kod · başlık · makine çipi · atanan · öncelik pimi · yaş ("3g").
- Detay çekmecesi: durum-duyarlı geçiş butonları (durum makinesi aynası) + yorum/aktivite akışı.
- Analiz: durum dağılımı · haftalık kapanış trendi · makine bazlı yük çubuğu.

**Dijital İkiz `/ikiz`** *(mevcut — rafine edilir)*
- SVG tesis şeması: ince ızgara zemin, hat-cyan bölge çerçeveleri, makine karoları
  (LED + OEE mini bar). Hover kartı: durum, pencere OEE'si, son veri zamanı.
- Düzenleme modu: palet + sürükle-yerleştir (çakışmasız ızgara yerleşimi) + bölge atama;
  kaydet = `PUT /ikiz/yerlesim` (replace-all). Saat penceresi seçici (`?saat=`).
- Yerleşmemiş makineler listesi kenar panelde; canlı olay → LED yenilemesiz değişir.

**Saha Cihazları `/saha/cihazlar`** — "MES/SCADA entegrasyon görünümü"
- KPI: kayıtlı cihaz · çevrimiçi (son görülme <5 dk) · bugün gelen ölçüm · protokol kırılımı.
- Cihaz kartları/grid: cihaz + eşlenen makine · protokol çipi (simülatör/OPC-UA/Modbus) ·
  canlı `son_gorulme` · çevrimiçi/çevrimdışı pimi · canlı mini sparkline (son ölçümler).

**Bakım Planları `/bakim-planlari`**
- KPI: aktif plan · bu hafta vadesi gelen · tür kırılımı (önleyici/kestirimci/periyodik).
- **Liste↔Takvim:** `TakvimZaman` görünümü (plan periyotları zaman şeridinde); tür pimi.
- F6·S24 sonrası: otomatik üretilen iş emri rozeti + MTBF/MTTR kartları makine detayında.

### 7.3 Stok & Satınalma (teal `#2dd4bf`)

**Malzemeler `/malzemeler`**
- KPI: toplam kalem · kritik altında · min altında · bugünkü hareket sayısı.
- Liste: malzeme varlık hücresi (kod + ad + birim) · bakiye (mono) · **stok/kritik
  `MiniBar`** (bakiye vs min/kritik eşikleri, semantik renk) · kritik pimi · `⋯`
  (hareket ekle, detay, satınalma talebi başlat).
- Analiz: kritik/normal dağılımı · hareket trendi (giriş/çıkış yığın çubuk).

**Malzeme Detay `/malzemeler/:id`** — seviye göstergesi (bakiye vs min/kritik/max)
· hareket geçmişi (tablo + trend) · ilgili satınalma talepleri · (F6·S25) lokasyon kırılımı.

**Kritik Stok `/stok/kritik`** — uyarı-odaklı: üstte `UyariKarti` özeti ("N kalem kritik
altında"), tablo kritik sıralı, satırdan **tek tık satınalma talebi oluştur** CTA.

**Satınalma Talepleri `/satinalma-talepleri`**
- KPI: onay bekleyen · bu ay onaylanan · reddedilen · toplam kalem tutarı/sayısı.
- **Liste↔Board:** kolonlar = taslak → onay bekliyor → onaylandı / reddedildi (iptal süzgeç).
  `VeriKart`: kod · kalem sayısı çipi · talep eden · yaş · durum pimi.
- Detay: kalem tablosu + onay aksiyonları (yalnız `satinalma:onay` — görev ayrımı UI'da
  `IzinKapisi` ile gizlenir, API 403 zaten garantili).

### 7.4 Kalite & Enerji (violet `#8b5cf6`)

**Kalite Kontrolleri `/kalite-kontrolleri`**
- KPI: bu ay kontrol · geçti oranı (mini trend) · kaldı sayısı · açık uygunsuzluk.
- Liste: sonuç pimi (geçti/kaldı) · makine/parti · denetçi · tarih.
- Analiz: geçti/kaldı trendi · hata türü **pareto** grafiği.

**Uygunsuzluklar (CAPA) `/uygunsuzluklar`**
- KPI: açık · doğrulamada · bu ay kapanan · ortalama kapanış süresi.
- **Liste↔Board:** 6 kolonlu CAPA akışı (açık → kök neden → aksiyon planı → uygulama →
  doğrulama → kapandı; kolon min-genişlik + yatay kaydırma). Kart: kod · başlık ·
  kaynak çipi · yaş · sorumlu.
- Detay: CAPA aşama zaman çizelgesi (`AktiviteAkisi`) · düzeltici/önleyici aksiyon alt
  tablosu · durum-duyarlı geçiş butonları (geçersiz geçiş zaten 409).

**Enerji `/enerji-tuketimleri`**
- KPI: bugünkü tüketim (kWh, mono) · saatlik ortalama · pik saat · dünle fark (Δ%).
- Analiz varsayılan görünümdür: trend alan grafiği (continuous aggregate) · saatlik
  **ısı haritası** · makine kırılımı; ham kayıt listesi ikincil sekme. Giriş formu korunur.

### 7.5 İSG & İK (amber `#f59e0b`)

**İş Kazaları `/is-kazalari`**
- KPI: **"X gündür kazasız"** (imza metrik, kiosk'a da aday) · bu yıl kaza · ramak kala ·
  kayıp gün.
- Liste: tür pimi (kaza/ramak kala) · yer · etkilenen · tarih. Analiz: aylık trend + tür kırılımı.

**Risk Değerlendirmeleri `/risk-degerlendirmeleri`**
- Üstte **5×5 `RiskMatrisi`** ısı görseli (hücrede sayaç; hücre tıkla → liste filtrelenir;
  mevcut saf `riskMatris.ts` beslenir). Liste: skor `MiniBar` + seviye pimi
  (çok düşük → çok yüksek) · alan/faaliyet · değerlendiren.

**Personeller `/personeller`**
- KPI: aktif personel · bugün izinli · süresi yaklaşan sertifika · açık zimmet.
- Liste: avatar varlık hücresi (ad + pozisyon) · birim · **maskeli TC** (mono; maskeleme
  sunucuda — KVKK) · durum pimi.

**Personel Detay `/personeller/:id`** — profil başlığı (avatar, ad, pozisyon, maskeli TC,
birim) + sekmeler: izinler · fazla mesailer · zimmetler (iade durumu pimli) · sertifikalar
(yaklaşan süre `UyariKarti`) + `AktiviteAkisi`. (F6·S26: izin hakediş bakiye kartı + org
şeması konumu.)

**İzin Talepleri `/izin-talepleri`**
- KPI: onay bekleyen · bu ay onaylanan · bugün izinli · reddedilen.
- **Liste↔Board:** taslak → onay bekliyor → onaylandı / reddedildi (+iptal süzgeç).
- Onay çekmecesi: tarih aralığı + tür + gerekçe + Onayla/Reddet (`ik:onay` görev ayrımı).
  (F6·S26: formda kalan hakediş günü göstergesi.)

### 7.6 Ticari (emerald `#34d399`)

**Ticari Pano `/ticari`** — KPI şeridi (firma · aktif sözleşme · açık talep · yaklaşan
sözleşme) korunur; üstüne **sözleşme durum donut'u** · **talep trendi** · yaklaşan
sözleşme zaman çizelgesi ("15 gün kaldı" çipleri) · son duyurular `AktiviteAkisi`.

**Firmalar `/firmalar`**
- KPI: müşteri · tedarikçi · aktif sözleşmeli · açık talebi olan.
- Liste: firma varlık hücresi · tür pimi (müşteri/tedarikçi) · ilişki sayaçları
  (ortak/sözleşme/talep çipleri) · şehir.
- **Firma Detay:** kimlik başlığı + sekmeler: ortaklar (kontaklar) · sözleşmeler ·
  talepler; (F6·S25) tedarikçi performans skoru kartı.

**Sözleşmeler `/sozlesmeler`**
- KPI: aktif · 30 gün içinde biten · taslak · toplam.
- **Liste↔Board** (durum makinesi kolonları) + üstte **"yaklaşan" uyarı şeridi**.
  Kart: `SZ-` kod · firma · bitiş tarihi + **kalan gün çipi** (30/15/7 eşik renkleri).
- Detay çekmecesi: `PanelKart` + `DurumPim` + `AktiviteAkisi` + durum geçiş butonları.

**Talepler `/talepler`**
- KPI: açık · atanmamış · bu hafta çözülen · ortalama yaş.
- **Liste↔Board** (durum makinesi); kart: `TL-` kod · firma · atanan · öncelik pimi · yaş
  (SLA eşik renklendirmesi F6).

### 7.7 Doküman & Duyuru (pink `#f472b6`)

**Belgeler `/belgeler`**
- KPI: toplam belge · kategori sayısı · bu ay yüklenen · toplam boyut.
- **Kart grid ↔ liste** (`GorunumGecis`): `VeriKart` = dosya türü ikonu · ad · kategori
  çipi · **sürüm rozeti (v3)** · boyut · güncelleyen + zaman.
- Detay: **sürüm zaman çizelgesi** (append-only; her sürüm indirilebilir) · multipart
  yükleme (sürükle-bırak alanı) · meta düzenleme.

**Duyurular `/duyurular`**
- **Akış (feed) kartları**: önem pimi (bilgi/önemli/kritik) · başlık · gövde özeti ·
  yayınlayan + zaman; `duyuru.yeni` olayı yeni kartı canlı vurguyla düşürür.
- Yayınlama formu korunur (`duyuru` izni); `DUY-` kod çipi.

### 7.8 Zekâ (fuşya `#d946ef`) — *v2'de yeni bölüm*

**AI Tahminleri `/tahminler`**
- Dört tahmin türü `Segmented` sekmeleri:
  - **Kestirimci bakım:** makine risk listesi — risk skoru `MiniBar` + seviye pimi;
    "bakım öner" → bakım planına derin bağlantı.
  - **Anomali:** son tespitler akışı (`AktiviteAkisi`) + zaman çizelgesi grafiği;
    `anomali.tespit` canlı düşer.
  - **OEE tahmini:** 7 gün ufuk çizgisi — gerçek (dolu) + tahmin (kesikli) alan grafiği.
  - **Stok ihtiyaç:** kalan gün + önerilen sipariş miktarı; kritik sıralı; satırdan
    satınalma talebi başlat.
- **Model şeffaflığı bandı:** aktif model sürümü çipi · son eğitim zamanı · eğitim geçmişi
  çekmecesi · "Eğit" aksiyonu (`ai:egit` görev ayrımı; 202 → ilerleme durumu canlı).

**Analitik `/analitik`**
- Dönem seçici (7/30/90 gün) + modül grupları `PanelKart` matrisi: üretim/OEE · makine ·
  iş emri · stok · kalite · enerji · İSG · bakım KPI'ları (tek `GET /analitik/kpi`).
- Günlük üretim/OEE **trend alan grafiği** (`/analitik/trend`).
- Her KPI kartından ilgili modül ekranına derin bağlantı ("kaynağa git").

**Raporlar `/raporlar`**
- Oluştur formu: tür (üretim/stok/kalite/enerji/iş emri) + dönem + format (PDF/XLSX).
- Durum akışlı liste: kuyrukta → hazırlanıyor (spinner pimi) → hazır / başarısız;
  `rapor.hazir` canlı düşer; **İndir** yalnız hazır durumda etkin (sunucu 409 zaten korur).
- Boş durum: rapor türlerini örnekleyerek öğretir.

### 7.9 Yönetim (slate `#94a3b8`)

**Kullanıcılar `/kullanicilar`**
- KPI: toplam kullanıcı · aktif · rol dağılımı (en kalabalık 3 rol çipi).
- Liste: kullanıcı varlık hücresi (avatar + ad + e-posta) · **rol çipleri** · durum pimi ·
  son giriş (F6·S23 denetim verisinden).
- Form: rol atama (çoklu; `GET /roller` beslemesi) · aktif/pasif.
- Bu bölüm F4–F6'da büyür: Abonelik & Modüller, Webhooklar, Sistem Sağlığı, Denetim
  Kaydı, Oturumlar, Bildirim tercihleri, Onaylarım (bkz. §11).

### 7.10 Kabuksuz ekranlar

- **Giriş `/giris`:** sol marka panelindeki animasyonlu üretim hattı imzası **korunur**
  (reduced-motion'da statik). 2FA adımı F6·S23'te aynı panele eklenir (kod girişi +
  kurtarma kodu bağlantısı).
- **Kiosk `/kiosk`:** uzak-okuma tipografi ölçeği (KPI 48–64px mono), 0 interaktif öğe,
  saat + canlı rozet, WS + 30 sn yoklama. Karo LED dili ikizle aynı. Uzun süreli ekran
  için: hafif ton varyasyonu / periyodik piksel kayması **opsiyonel** (OLED yanık koruması).
  "X gündür kazasız" karosu aday (İSG verisi, `kiosk` rolü kapsamı genişletilmeden —
  yalnız `uretim:oku` kalırsa karo gizli).
- **Önizleme `/onizleme`:** yalnız DEV; yeni primitiflerin vitrin sayfası olarak da kullanılır.

---

## 8. Katman 4 — Panolar (grafik-zengin)

- `modules/pano/PanoIcerik.tsx` (360°): §7.1'deki hedef düzen; mevcut KPI+gauge+donut
  korunur, trend alanı + uyarı şeridi + makine kartları + enerji mini özeti eklenir.
- `modules/ticari/TicariPano.tsx`: §7.6'daki hedef düzen (donut + trend + zaman çizelgesi
  + duyuru akışı).
- `modules/analitik/AnalitikPano.tsx`: §7.8 düzeni; pano ile analitik arasındaki fark
  netleşir — *pano = şimdi ne oluyor*, *analitik = dönemsel nasıl gidiyor*.

## 9. Katman 5 — Detay ekranları (zengin profiller)

Tek `SayfaBaslik + Card` yerine profil düzeni (kimlik başlığı + sekmeler/paneller + timeline):
`MakineDetay`, `MalzemeDetay`, `PersonelDetay`, `FirmaDetay` (§7'de ekran ekran yazıldı).
Sözleşme/Belge/Talep/İzin/Uygunsuzluk/Satınalma detay **çekmeceleri** `PanelKart` +
`DurumPim` + `AktiviteAkisi` + durum-geçiş butonlarıyla yeniden düzenlenir (mantık aynı).

## 10. Katman 6 — Backend özet uçları (küçük, salt-okunur)

Her modül için `GET /<kaynak>/ozet` → durum sayıları / anahtar toplamlar döndüren hafif
toplulaştırma ucu. **Şema değişmez (migration yok).** `tenant-rbac-conventions` +
`turkce-identifier-standardi`: tenant `search_path`-izole sorgu, ilgili `<modul>:oku`
izniyle korunur, yanıt zarfı standart. Mevcut `GET /ticari/ozet`, `PanoOzet` ve
`GET /analitik/kpi` desenleri örnek alınır; analitik ile çift hesap yapılmaz —
ortak hesap fonksiyonları paylaşılır.

**Uçlar (temsili):** `/uretim/ozet`, `/stok/ozet`, `/satinalma/ozet`, `/kalite/ozet`,
`/enerji/ozet`, `/isg/ozet`, `/ik/ozet`, `/sozlesme/ozet`, `/talep/ozet`, `/dys/ozet`,
`/duyuru/ozet`, `/kullanici/ozet`, `/tahmin/ozet`, `/rapor/ozet` (mevcut `ticari/ozet`,
kritik stok, pano, analitik yeniden kullanılır). Her uca frontend `use<Modul>Ozet()`
hook'u + OpenAPI `npm run codegen`. Her uç için backend testi (izolasyon + RBAC 403 +
doğru sayım).

---

## 11. Gelecek fazların UI planı (henüz yapılmadı — tasarım sözleşmesi)

> Bu bölüm, yol haritasındaki ⬜ sprintlerin arayüz sözleşmesidir; ilgili sprint
> açıldığında buradaki spec başlangıç noktasıdır ve aynı desen sözlüğü (§4–§6) kullanılır.

### 11.1 Faz 4 — Lisanslama & Dış Entegrasyon

**S16 — Abonelik & Modüller `/abonelik` (Yönetim, slate):**
- Plan kartı: plan adı + dönem + yenileme tarihi; **koltuk kullanımı** progress
  (`kullanılan/limit`, eşik renkli).
- **Modül entitlement matrisi:** modül kartları (hat rengi ikonlu) açık/kapalı durumu +
  limitler; feature flag rozetleri ("deneysel").
- Menü entitlement süzgeci: kapalı modül menüde görünmez; doğrudan URL'ye gidilirse
  **"modül kapalı" upsell boş durumu** (BosDurum + plan yükselt CTA) — API 403'ü zarif karşılar.

**S17 — Platform Admin Paneli (ayrı SPA `platform.*`):**
- Aynı token sistemi; ayrı kimlik: **"platform" hat rengi** (turuncu `#f97316` önerisi —
  tenant UI'ında kullanılmıyor, karışmaz) + kabukta kalıcı "PLATFORM" filigran çipi
  (hangi düzlemde olduğun her an belli — yanlış düzlemde işlem riskine karşı).
- Ekranlar: tenant listesi (durum/plan/kullanım + sağlık pimi) · tenant detay (abonelik,
  kullanıcı sayısı, kaynak kullanımı) · **provizyon sihirbazı** (`AdimSihirbaz`: slug →
  plan → admin hesabı → özet; dakikalar içinde canlı) · platform sağlık panosu.
- **Tehlikeli aksiyon deseni:** askıya alma / ihraç / silme → ad-yazarak-onayla modalı
  (GitHub deseni); ihraç 202 async + indirilebilir arşiv.

**S18 — Dış Portal (ayrı hafif kabuk, `dis-panel`) + Webhook yönetimi:**
- Portal: aynı antrasit ailenin sadeleştirilmiş tek-modül kabuğu (sidebar yok, üst
  sekme: Taleplerim · Yeni Talep); talep detayında **durum zaman çizelgesi**
  (müşteri-dili durum adları); markalama alanı (tenant logosu).
- Webhook yönetimi (iç panel, Yönetim): abonelik listesi (URL, olay türleri çipleri,
  **maskeli secret** + kopyala) · **teslimat günlüğü** (durum pimi: başarılı/yeniden
  deneniyor/başarısız + yanıt kodu + payload görüntüle çekmecesi + "yeniden dene").

### 11.2 Faz 5 — Operasyon & GA

- **S19 — Sistem Sağlığı `/sistem-sagligi`:** servis kartları (db/redis/minio/mqtt —
  LED dili) · SLI/SLO göstergeleri · son hatalar (Sentry derin bağlantısı). Grafana'nın
  yerini almaz; yöneticinin "her şey yolunda mı" ekranıdır.
- **S21 — Onboarding sihirbazı:** boş tenant ilk girişte `AdimSihirbaz`: fabrika profili →
  makineleri ekle (form veya CSV) → rolleri/davetleri gönder → örnek veri iste. Tüm boş
  durum CTA'ları sihirbazın ilgili adımına bağlanır.
- **S22 — GA cilası:** klavye kısayol haritası (`?` overlay) · yazdırma stilleri ·
  son erişilebilirlik/kontrast denetimi.

### 11.3 Faz 6 — Kurumsal Derinleşme (yol haritası S23–S28 ile birebir)

**S23 — Güvenlik & Uyum:**
- **Denetim Kaydı `/denetim-kayitlari`:** `FiltreCubugu` (kullanıcı/kaynak/eylem/tarih) +
  tablo (kim-ne-ne zaman, istek id) + **fark çekmecesi** (öncesi/sonrası alan farkları).
- **Oturumlar `/oturumlar`:** aktif oturum/cihaz listesi (tarayıcı, IP, son etkinlik) +
  uzaktan sonlandır (tehlikeli aksiyon onayı).
- **2FA kurulumu:** profil menüsünden `AdimSihirbaz` (QR → kod doğrula → kurtarma
  kodları — bir kez gösterilir, kopyala/indir).
- **KVKK self-servis:** ihraç talebi oluştur → durum akışlı liste (rapor deseniyle aynı) → indir.

**S24 — Üretim derinleşmesi:** Vardiyalar (`TakvimZaman` haftalık şablon) · Duruş
Kayıtları (makine zaman şeridi + **neden pareto**su; OEE ekranlarına "duruş kaynaklı"
kırılım gelir) · **Ürün/BOM `AgacGorunum`** editörü (reçete kalemleri → malzeme bağlama;
iş emri formuna ürün seçimi) · İzlenebilirlik sorgusu (lot gir → ileri/geri zincir
diyagramı) · Makine detayına MTBF/MTTR kartları.

**S25 — Tedarik zinciri:** Depo/Lokasyon `AgacGorunum` · **Sayım oturumu** (mobil-dostu
sayım girişi; fark tablosu semantik renkli; onay aksiyonu ayrı izinle) · Barkod etiketi
üret (PDF) · **Satınalma Siparişleri** liste↔board (`SS-` kod; teslim alma formu kısmi
kabul destekli; talep→sipariş→teslim zinciri `AktiviteAkisi`) · Firma detayına tedarikçi
performans sekmesi (zamanında teslim + kalite skoru).

**S26 — Kalite/İSG/İK tamamlama:** Kontrol planları (ürün başına karakteristik tablosu) ·
**SPC ekranı** (X̄-R kontrol grafiği `kontrolGrafikSecenek`; kural ihlali noktaları
işaretli + ihlal listesi) · Kalibrasyon takvimi (`TakvimZaman` + yaklaşan `UyariKarti`) ·
İSG eğitim matrisi (personel × eğitim ısı haritası) · İzin hakediş bakiyesi (personel
detay kartı + izin formunda "kalan gün") · **Org şeması** (`AgacGorunum` salt-okunur).

**S27 — Platform deneyimi (bu planın tamamlanma sprinti):**
- **Bildirim merkezi:** `BildirimPaneli` (zil → liste, okundu yönetimi) +
  `/bildirim-tercihleri` (olay türü başına anahtar; e-posta kanalı).
- **Onaylarım `/onaylarim`:** satınalma + izin + sayım düzeltme bekleyenleri tek listede;
  satırdan onay/ret; rol-duyarlı (yalnız yetkili olduğun türler görünür).
- **⌘K içerik arama:** palet gezinmeye ek kayıt arama (makine/malzeme/firma/belge/iş
  emri/personel; RBAC süzgeçli; sonuç grubu başına modül hat rengi noktası).
- **İçe/dışa aktarma:** her liste ekranında `DisaAktarMenu` (CSV/XLSX; büyük veri 202
  async → raporlar deseniyle indir); içe aktarma sihirbazı (dosya → kolon eşleme →
  önizleme/doğrulama → uygula).
- Yazdırma şablonları (rapor + etiket + PO).
- Erişilebilirlik pası: klavye/odak/aria; hedef Lighthouse a11y ≥ 95.

**S28 — Güvence:** UI etkisi sınırlı — "Yenilikler" (sürüm notları) paneli + geliştirici
API portalı (OpenAPI'den statik site, ayrı ürün) + klavye kısayol haritası son hâli.

---

## 12. i18n

Yeni etiketler (KPI başlıkları, "Liste/Board/Analiz", özet metrikleri, komut paleti,
boş durumlar, gelecek faz ekranları) `frontend/src/i18n/tr.json` (birincil) + `en.json`'a
eklenir. Testler görünür Türkçe metne bağlı olduğundan **mevcut anahtarlar korunur**;
yeni anahtarlar eklenir. Dış Portal (F4) tenant markalamasıyla birlikte kendi i18n alt
kümesini taşır (müşteri-dili durum adları).

## 13. Testler (kırılmaması gereken sınırlar)

- Frontend testleri **test-id değil, Türkçe i18n metni + ARIA rol** üzerinden çalışır
  (`columnheader`, `button`, `textbox`, placeholder "Ara"). Semantik AntD yapısı ve i18n
  metinleri **korunur**; değişen yapılarda testler aynı adımda güncellenir.
- Saf mantık testleri (`durum.test.ts`, `izinDurum.test.ts`, `riskMatris.test.ts`,
  `panoVeri.test.ts`, `menu.test.ts`, `grafikSecenek.test.ts`) dokunulmadan geçmeli.
- Yeni primitif testleri: `OzetSerit`, `MiniTrend`/`MiniBar`, `DurumPim`, `KanbanPano`,
  `GorunumGecis`, `KomutPaleti`, `RiskMatrisi`, `TakvimZaman`; F4+/F6 primitifleri
  (`AdimSihirbaz`, `AgacGorunum`, `BildirimPaneli`, `DisaAktarMenu`) kendi sprintlerinde.
- Yeni grafik üreticileri `grafikSecenek.test.ts`'e eklenir (saf, deterministik).
- Backend: her `/ozet` ucu için pytest (tenant izolasyon + RBAC 403 + sayım doğruluğu).

## 14. Doğrulama (uçtan uca)

1. **Lint/tip/test:** `ruff` + `mypy` + backend `pytest`; frontend `eslint` + `tsc` + `vitest`.
2. **`npm run codegen`** ile OpenAPI tipleri yenilenir (yeni `/ozet` uçları).
3. **Canlı tarayıcı turu (Playwright MCP):** demo tenant (`demo` / admin@demo.test /
   `Demo1234!`) ile dev sunucu ayakta; yeniden tasarlanan her ekran gezilir + ekran
   görüntüsü: pano → her modül liste (Liste/Board/Analiz geçişleri) → detay profilleri →
   ikiz/kiosk → komut paleti (⌘K) → koyu tema tutarlılığı + hat rengi kimliği +
   responsive (`lg` altında sidebar çekmece).
4. `verify` skill'i ile en az bir tam akış (ör. iş emri/sözleşme board'da durum geçişi)
   gerçek uygulamada sürülerek doğrulanır.

## 15. Uygulama sırası (dalgalar)

| Dalga | Kapsam | Çıktı |
|---|---|---|
| 1 | Katman 1 primitifler + grafik üreticileri + `/ozet` uçları (ilk 4 modül) | Desen sözlüğü hazır, `/onizleme` vitrini |
| 2 | Temsilci ekranlar (§7'deki 8 temsilci) + kabuk rafinasyonu | Desen kanıtlanmış |
| 3 | Kalan tüm liste ekranları + board görünümleri + kalan `/ozet` uçları | Tüm modüller çalışma alanı |
| 4 | Panolar (360°/Ticari/Analitik) + detay profilleri + komut paleti | Grafik-zengin bütünlük |
| 5 | Cila: boş durumlar, animasyon, responsive, a11y pası + canlı tur | Yayına hazır |
| F4–F6 | §11'deki ekranlar kendi sprintlerinde bu plana göre | Sözleşme hazır |

## 16. Riskler / notlar

- **Kapsam büyük:** primitifler önce inşa edilip sonra ekranlara uygulanır (tekrar
  minimum, tutarlılık garanti). Dalga planı (§15) tek-pas riskini böler.
- **Restrained felsefe korunur:** hat rengi ~%2-3 yüzeyde; grafik çok-renk yalnız veri
  serisi ayrımı için. `DESIGN.md` güncellenerek tek doğruluk kaynağı korunur.
- **Geriye uyum:** `SunucuTablo`/`KpiKart` API'leri eklemeli (opsiyonel prop) genişletilir;
  mevcut çağrılar bozulmaz.
- **Kiosk/ikiz istisnası:** bu iki ekran zaten imza kalitesinde; yalnız desen sözlüğüne
  (LED/pim/mono) hizalanır, yeniden tasarlanmaz.
- **Gelecek faz spec'leri sözleşmedir, taahhüt değildir:** sprint açıldığında ADR ile
  detaylandırılır; bu plan başlangıç noktasıdır.
