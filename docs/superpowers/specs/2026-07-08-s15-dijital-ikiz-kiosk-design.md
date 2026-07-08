# S15 Tasarım — Dijital İkiz + Kiosk (Faz 3 / Zekâ)

Plan kaynağı: `docs/yol-haritasi.md` §S15. Amaç: **dijital ikiz görselleştirme**
(tesis/hat şeması, canlı makine durumu) + **kiosk** salt-okunur, oturum-dayanıklı
büyük ekran üretim panosu.

## Kapsam

- **İkiz yerleşimi (`modules/ikiz/`):**
  - Model `IkizDugum` (`ikiz_dugumleri`, tenant şeması): `makine_id` (FK `makineler`,
    **unique** — bir makine şemada bir kez), `x`/`y` Float (**yüzde koordinat 0–100**,
    şema çözünürlükten bağımsız), `bolge` String(100) default "" (hat/alan etiketi).
    Migration down `b4e8f2a6c159`; hypertable/CAGG yok; fan-out up/down testli.
  - `GET /ikiz/yerlesim` (`uretim:oku`) — düğüm listesi.
  - `PUT /ikiz/yerlesim` (`uretim:yaz`) — **replace-all** (idempotent): gövde düğüm
    listesi; x/y 0–100 doğrulanır (422), gövdede mükerrer `makine_id` 422, var olmayan
    makine 422 (alan-detaylı). Audit + best-effort `ikiz.yerlesim` gerçek-zaman yayını
    (outbox yok — UI kaygısı).
- **Canlı durum ucu — kiosk'un da tek veri kaynağı:**
  - `GET /ikiz/durum?saat=24` (`uretim:oku`; saat 1–168) tek çağrıda:
    - `ozet`: makine toplam + durum kırılımı, pencere üretim toplamları
      (toplam/sağlam adet, fire oranı), **dönem OEE** (bileşen toplamlarından
      `analitik.hesap.donem_oee` — S14 matematiği yeniden kullanılır), açık arıza sayısı.
    - `dugumler`: yerleşim ⋈ makine — kod/ad/durum + x/y/bolge + makine-başı pencere
      OEE'si + toplam adet + `son_veri_zamani`.
    - `yerlesmemis`: şemaya konmamış makineler (kod/ad/durum) — düzenleme paleti.
  - Yeni olay tanımı gerekmez: `makine.durum` + `uretim.eklendi` (S7) zaten yayınlanır;
    frontend bunlarla `ikiz` sorgusunu invalidate eder.
- **RBAC / kiosk salt-okunurluğu:** yeni rol **`kiosk`** = {`uretim:oku`} (en az
  ayrıcalık). Salt-okunurluk yalnız UI değil **API seviyesinde** garanti: kiosk rolü
  ile her yazma ucu 403 (testli). İzin kodu eklenmez (katalog yeterli).
- **Frontend — Dijital ikiz (`/ikiz`, menü Üretim bölümü, `uretim:oku`):**
  - `modules/ikiz/{sunum.ts, hooks.ts, IkizSayfasi.tsx}`. SVG tesis şeması
    (viewBox yüzde-tabanlı): makine kutuları durum-renkli LED + kod + mini OEE barı;
    bölge etiketleri; düğüme tıkla → detay (durum, OEE, üretim, makine sayfası linki).
  - **Düzenleme modu** (`uretim:yaz` görünür): sürükle-taşı (pointer events, yüzde
    kırpma `sunum.ts`'te saf+testli), yerleşmemiş makine paleti (tıkla-yerleştir),
    düğüm kaldırma, Kaydet → `PUT /ikiz/yerlesim`, Vazgeç → sunucu durumuna dön.
  - Canlı: `makine.durum`/`uretim.eklendi`/`ikiz.yerlesim` → `ikiz` invalidate.
- **Frontend — Kiosk (`/kiosk`):**
  - `modules/kiosk/KioskSayfasi.tsx` — **kabuksuz** tam ekran rota (KorunanRota içinde,
    `UygulamaKabugu` dışında; kendi `GercekZamanSaglayici` sargısı). Büyük ekran panosu:
    saat + tenant + canlı rozeti başlığı; dev KPI kartları (pencere üretim, OEE, çalışan
    makine x/y, açık arıza, fire); makine karo ızgarası (durum renk + OEE oran barı +
    son veri zamanı). Hiç yazma aksiyonu yok.
  - **Oturum-dayanıklılık:** mevcut sessiz giriş (refresh localStorage + rotasyon) sayfa
    yenilemede oturumu korur; WS oto-reconnect + **30 sn yoklama** (`refetchInterval`)
    ağ kopsa da toparlar; istek hatasında son veri ekranda kalır + "bağlanıyor" rozeti.
  - Giriş: ikiz sayfası başlığından "Kiosk modu" butonu; kiosk'tan logo tıklaması `/`'e döner.

## Kapsam dışı (bilinçli)

- Leaflet/gerçek kat planı görüntüsü altlığı (SVG şema yeterli; altlık görseli Faz 5
  cilası olabilir). 3B/animasyonlu ikiz yok.
- Kiosk için ayrı kimlik mekanizması (cihaz token'ı vb.) — mevcut JWT + `kiosk` rolü
  yeterli; cihaz bazlı kayıt S16 entitlement/S18 dış erişimle birlikte düşünülür.
- Sensör-düzeyi ikiz (sıcaklık/titreşim overlay) — S8 ölçümleri `uretim_verileri`nde;
  makine-durum + OEE görselleştirmesi kabul kriterini karşılar.

## Kabul kriterleri (plandan)

1. **İkiz canlı makine durumunu yansıtır:** makine durumu değişince (`makine.durum`
   olayı) ikiz görünümü manuel yenileme olmadan güncellenir; durum ucu sayısal doğru
   (bilinen sentetik veriyle OEE/adet doğrulaması testli).
2. **Kiosk salt-okunur:** `kiosk` rolü ile tüm yazma uçları 403 (API testi); kiosk
   ekranında hiçbir yazma aksiyonu yok.
3. **Kiosk oturum-dayanıklı:** sayfa yenilemede oturum korunur (sessiz giriş), veri
   yoklama + WS ile kendini tazeler.
4. Yerleşim uçları `uretim:oku`/`uretim:yaz` korumalı; tenant izole (A'nın yerleşimi
   B'de görünmez); migration fan-out up/down testli; `ikiz_dugumleri` veri sözlüğünde.
