# ADR-0017: Dijital İkiz + Kiosk — ince yerleşim katmanı + salt-okunur büyük ekran

Durum: Kabul
Tarih: 2026-07-08

## Bağlam
Faz 3 / S15: tesisin **canlı sayısal yansıması** (dijital ikiz: tesis/hat şeması üzerinde
makine durumları) ve sahaya asılacak **kiosk** büyük ekran üretim panosu. Plandaki
teknoloji önerisi "SVG/Leaflet"; kabul kriterleri: ikiz canlı makine durumunu yansıtır,
kiosk salt-okunur + oturum-dayanıklı.

Mevcut altyapı yeniden kullanılır: makine durumu + üretim verileri (ADR-0006), Redis
pub/sub gerçek-zaman `makine.durum`/`uretim.eklendi` olayları (ADR-0009), dönem OEE
saf hesabı (ADR-0016), sessiz giriş/refresh rotasyonu (ADR-0008).

## Karar
- **İkiz = mevcut verinin üstünde ince yerleşim katmanı.** Tek yeni tablo
  `ikiz_dugumleri` (makine_id **unique** FK, `x`/`y` **yüzde koordinat 0–100**, `bolge`
  etiketi). Canlı durum bu tabloda tutulmaz — `makineler.durum` + `uretim_verileri`
  penceresinden okunur; ikiz hiçbir veriyi çoğaltmaz. Yüzde koordinat şemayı ekran
  çözünürlüğünden bağımsız kılar.
- **SVG, Leaflet değil.** Şema bir harita değil topolojik hat görünümüdür; Leaflet'in
  tile/projeksiyon altyapısı gereksiz bağımlılık olurdu. Frontend yüzde koordinatları
  doğrudan SVG viewBox'ına çizer; sürükle-yerleştir düzenleme pointer olaylarıyla yapılır.
- **Yerleşim yazımı `PUT /ikiz/yerlesim` replace-all (idempotent).** Düğüm sayısı düşük
  (≤ birkaç yüz makine); diff/patch API karmaşası yerine şemanın tamamı tek istekte
  değiştirilir. Doğrulama: mükerrer/bilinmeyen makine → 422 (alan detaylı). Başarıda
  best-effort `ikiz.yerlesim` gerçek-zaman yayını — outbox'a yazılmaz (UI tazeleme
  kaygısı; `rapor.hazir` ile aynı ayrım, ADR-0016).
- **`GET /ikiz/durum` tek uç — ikiz ekranı ve kiosk aynı kaynaktan beslenir.** Yerleşim
  ⋈ makine (kod/ad/canlı durum) + makine-başı pencere OEE'si/üretim toplamı/son veri
  zamanı + **yerleşmemiş** makineler (düzenleme paleti) + tesis özeti (durum kırılımı,
  toplam/sağlam adet, fire, dönem OEE, açık arıza). Pencere `?saat=` (1–168, varsayılan
  24). OEE `analitik.hesap.donem_oee` ile türetilir — ikinci bir OEE tanımı doğmaz.
- **Kiosk = ayrı uygulama değil, kabuksuz rota + `kiosk` rolü.** `/kiosk` SPA içinde
  `UygulamaKabugu` dışında tam ekran render edilir (menü/aksiyon yüzeyi yok). Yeni rol
  `kiosk` = {`uretim:oku`} (en az ayrıcalık): salt-okunurluk UI vaadi değil **API
  garantisidir** — kiosk kimliğiyle her yazma ucu 403 (testli). Yeni izin kodu eklenmedi;
  ikiz üretim modülünün görünümüdür (`uretim:oku`/`uretim:yaz`), modül-bazlı entitlement
  gerekirse S16'da ayrışır.
- **Oturum-dayanıklılık mevcut mekanizmalarla.** Refresh token + sessiz giriş (ADR-0008)
  sayfa yenilemede oturumu korur; WS oto-reconnect (ADR-0009) + 30 sn `refetchInterval`
  yoklaması ağ kopmalarını toparlar; istek hatasında son bilinen veri ekranda kalır,
  yalnız bağlantı rozeti düşer. Kiosk'a özel uzun ömürlü cihaz token'ı bilinçli
  ertelendi (S16/S18 dış erişim tasarımıyla birlikte).

## Sonuçlar
- (+) İkiz canlılığı yeni olay altyapısı istemedi: `makine.durum`/`uretim.eklendi`
  aboneliği ikiz sorgusunu invalidate eder; yerleşim değişikliği `ikiz.yerlesim` ile yayılır.
- (+) Tek durum ucu kiosk'u tek istekle besler (KPI + karolar); sayısal doğruluk izole
  `ikiz` tenant'ında elle hesaplanan değerlerle test edildi; izolasyon + RBAC 403 testli.
- (−) Yerleşim replace-all eşzamanlı iki düzenleyicide "son yazan kazanır" davranır;
  düğüm-bazlı kilitleme/versiyonlama düşük öncelikle ertelendi (tek tesis yöneticisi varsayımı).
- (−) `/ikiz/durum` her istekte canlı toplar (önbellek yok); pencere sorgusu makine-bazlı
  GROUP BY ile ucuz, hacim büyürse S19'da continuous aggregate değerlendirilir.
- (−) Kiosk cihaz yönetimi (uzak provizyon, kayıt ekranı) kapsam dışı; giriş bir kez
  elle yapılır, oturum refresh'le yaşar.

## Notlar
- Migration `c9e6f2a8d135` (down `b4e8f2a6c159`); 1 tablo (`ikiz_dugumleri`), hypertable
  yok; fan-out up/down testli (`test_s15_migration.py`).
- Uçlar: `GET/PUT /ikiz/yerlesim`, `GET /ikiz/durum`. Realtime: `ikiz.yerlesim` (yeni),
  `makine.durum`/`uretim.eklendi` (mevcut). Rol: `kiosk`.
- Frontend: `/ikiz` (SVG şema + düzenleme modu), `/kiosk` (kabuksuz büyük ekran).
