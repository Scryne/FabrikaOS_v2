# Veri Sözlüğü (Ubiquitous Language)

Kod tanımlayıcıları **Türkçe-ASCII** (ç/ş/ı/ğ/ö/ü yok). Bir kavram tüm projede tek
kelimeyle anılır. Yeni terim eklerken buraya yaz.

## Genel terimler
| Terim | Açıklama |
|---|---|
| MES | Manufacturing Execution System — üretim yürütme sistemi (saha seviyesi) |
| ERP | Enterprise Resource Planning — kurumsal kaynak planlama |
| OEE | Overall Equipment Effectiveness = Kullanılabilirlik × Performans × Kalite |
| Multi-tenant | Çok kiracılı; tek platform, izole fabrika verileri |
| Control-plane | `public` şeması: tenant, abonelik, entitlement, platform yönetimi |
| Entitlement | Tenant'ın hangi modüllere/limitlere erişebildiği (lisans/plan) |
| Edge Gateway | Sahada PLC/sensörden okuyup MQTT'ye yollayan ajan |
| Hypertable | TimescaleDB zaman-serisi tablosu |
| RBAC | Role-Based Access Control — rol tabanlı yetkilendirme |
| Digital twin | Dijital ikiz — tesisin canlı sayısal yansıması |
| Provisioning | Yeni tenant'ın otomatik kurulumu (şema + migrate + seed) |
| search_path | PostgreSQL şema arama yolu; tenant izolasyonu burada `tenant_<slug>, public` olur |
| Fan-out | Bir migrasyonu `public` + tüm aktif tenant şemalarına uygulama |
| Durum makinesi | İş emri yaşam döngüsü geçiş kuralları (`acik→atandi→devam_ediyor→kapandi`, `iptal`) |
| Domain olayı | İş kuralı sonucu üretilen olay (ör. `is_emri.kapandi`); webhook'la dışa iletilir (S18) |
| Transactional outbox | Olayı üreten iş ile aynı transaction'da `giden_olaylar`'a yazma deseni (kayıpsız teslim) |
| JWT | JSON Web Token; access (kısa) + refresh (rotasyonlu) |
| Refresh rotasyonu | Yenilemede eski refresh'i iptal edip yeni çift üretme (Redis iptal listesi) |
| RPO / RTO | Kabul edilebilir veri kaybı / kurtarma süresi (DR) |
| KVKK | Kişisel Verilerin Korunması Kanunu; özlük veri minimizasyonu + erişim kısıtı (TC maskeleme) |
| Risk matrisi | Olasılık × Şiddet (1..5) → risk skoru (1..25) → risk seviyesi (dusuk/orta/yuksek/cok_yuksek) |

## Identifier sözlüğü (tablo/model/kolon)
| Kavram | Identifier (tekil / çoğul) |
|---|---|
| Makine | `makine` / `makineler` |
| Üretim verisi | `uretim_verisi` / `uretim_verileri` |
| İş emri | `is_emri` / `is_emirleri` |
| İş emri yorumu | `is_emri_yorum` / `is_emri_yorumlari` |
| Bakım planı | `bakim_plani` / `bakim_planlari` |
| Giden olay (outbox) | `giden_olay` / `giden_olaylar` |
| Arıza | `ariza` / `arizalar` |
| Saha cihazı (edge gateway) | `cihaz` / `saha_cihazlar` |
| Alınan ölçüm (idempotency defteri) | `alinan_olcum` / `saha_alinan_olcum` |
| Ölçüm paketi (kontrat DTO) | `OlcumPaketi` (`olcum_id`, `makine_kod`, OEE girdileri) |
| Malzeme | `malzeme` / `malzemeler` |
| Stok hareketi | `stok_hareketi` / `stok_hareketleri` |
| Satınalma talebi | `satinalma_talebi` / `satinalma_talepleri` |
| Satınalma talebi kalemi | `satinalma_talebi_kalemi` / `satinalma_talebi_kalemleri` |
| Kullanıcı | `kullanici` / `kullanicilar` |
| Rol / İzin | `rol` / `roller`, `izin` / `izinler` |
| Personel (İK, KVKK: TC maskeli) | `personel` / `personeller` |
| İzin talebi (İK, onay akışı) | `izin_talebi` / `izin_talepleri` |
| Fazla mesai (İK) | `fazla_mesai` / `fazla_mesailer` |
| Zimmet (demirbaş atama, İK) | `zimmet` / `zimmetler` |
| Sertifika / eğitim (İK) | `sertifika` / `sertifikalar` |
| İş kazası (İSG) | `is_kazasi` / `is_kazalari` |
| Risk değerlendirme (İSG, risk matrisi) | `risk_degerlendirme` / `risk_degerlendirmeleri` |
| Kalite kontrol | `kalite_kontrol` / `kalite_kontrolleri` |
| Uygunsuzluk (CAPA) | `uygunsuzluk` / `uygunsuzluklar` |
| CAPA aksiyonu (düzeltici/önleyici) | `capa_aksiyon` / `capa_aksiyonlari` |
| Enerji tüketim | `enerji_tuketim` / `enerji_tuketimleri` |
| Enerji tüketim (saatlik CAGG) | `enerji_tuketim_saatlik` (continuous aggregate) |
| Firma (CRM, müşteri/tedarikçi) | `firma` / `firmalar` |
| Ortak (CRM, firma ilgili kişisi) | `ortak` / `ortaklar` |
| Sözleşme (durum makinesi + yaklaşan bitiş) | `sozlesme` / `sozlesmeler` |
| Talep (durum makinesi) | `talep` / `talepler` |
| Belge (DYS) | `belge` / `belgeler` |
| Belge sürümü (DYS, append-only, nesne depolama) | `belge_surumu` / `belge_surumleri` |
| Duyuru (gerçek-zaman `duyuru.yeni`) | `duyuru` / `duyurular` |
| Model kaydı (AI, sürümlü artefakt üstverisi) | `model_kaydi` / `model_kayitlari` |
| Tahmin (AI çıkarım geçmişi, append-only) | `tahmin` / `tahminler` |
| Rapor (async üretilen PDF/XLSX, nesne depolama) | `rapor` / `raporlar` |
| İkiz düğümü (tesis şemasında makine konumu, yüzde koordinat) | `ikiz_dugum` / `ikiz_dugumleri` |
| Denetim izi (audit) | `denetim_izi` |
| Tenant | `tenant` / `tenantlar` |
| Abonelik | `abonelik` / `abonelikler` |
| Plan (satış planı: modül seti + koltuk limiti, public) | `plan` / `planlar` |
| Modül hakkı (entitlement override, tenant-başına, public) | `modul_hakki` / `modul_haklari` |
| Özellik bayrağı (feature flag override, tenant-başına, public) | `ozellik_bayragi` / `ozellik_bayraklari` |
| Koltuk (seat — aktif kullanıcı üst sınırı) | `koltuk` / `koltuk_limiti` |
| Platform yöneticisi (control-plane operatörü, public) | `platform_yonetici` |
| Tenant ihracı (KVKK dışa aktarma işi, public) | `tenant_ihrac` / `tenant_ihraclari` |
| Platform denetim izi (control-plane audit, public) | `platform_denetim_izi` |

## Ortak kolonlar
`olusturma_tarihi`, `guncelleme_tarihi`, `olusturan_id`, `durum`, `<x>_id` (FK).

## İzin formatı
`modul:islem` → `uretim:oku`, `uretim:yaz`, `uretim:sil`, `isemri:yaz`, `stok:oku`,
`satinalma:onay`, `isg:oku`, `isg:yaz`, `ik:oku`, `ik:yaz`, `ik:onay`, `crm:oku`, `crm:yaz`,
`sozlesme:oku`, `sozlesme:yaz`, `talep:oku`, `talep:yaz`, `dys:oku`, `dys:yaz`, `duyuru:oku`,
`duyuru:yaz`, `ai:oku`, `ai:egit`, `analitik:oku`, `rapor:oku`, `rapor:yaz`,
`abonelik:oku`, `platform-admin`, `dis-panel`. Görev ayrımı: `satinalma:onay` ve `ik:onay` yalnız
onaylayan rollerde; `ai:egit` (model eğitimi) `ai:oku`'dan (tahmin görüntüleme),
`rapor:yaz` (rapor üretme) `rapor:oku`'dan (görüntüleme/indirme) ayrıdır.

## Nesne depolama (DYS + AI + Rapor)
Belge içerikleri, AI model artefaktları ve rapor dosyaları ilişkisel DB'de değil
**nesne deposunda** (MinIO/S3) tutulur; tenant izolasyonu anahtar önekiyle:
`tenant_<slug>/belge/<belge_id>/<surum>/<dosya>` (DYS),
`tenant_<slug>/model/<tur>/<surum>/model.joblib` (AI, joblib serileştirme),
`tenant_<slug>/rapor/<rapor_id>/<dosya>` (S14 raporları). Soyutlama
`NesneDepo` (`MinioNesneDepo` gerçek + `BellekNesneDepo` test). Sürümler append-only.

## AI model türleri (S13)
`kestirimci_bakim` (makine başına arıza riski + seviye), `anomali` (makine-gün aykırılık,
`anomali.tespit` olayı), `oee` (makine başına 7 günlük OEE tahmini), `stok` (malzeme başına
kalan gün + önerilen sipariş). Model durumu: `egitiliyor → hazir | basarisiz`; tur başına
tek `aktif` sürüm.

## Rapor türleri ve yaşam döngüsü (S14)
Türler: `uretim` (gün×makine OEE dökümü), `stok` (bakiye/kritik durum), `kalite`
(dönem kontrolleri), `enerji` (günlük tür+birim tüketim), `isemri` (dönem iş emirleri).
Biçimler: `pdf` (ReportLab) | `xlsx` (openpyxl). Durum: `kuyrukta → hazirlaniyor →
hazir | basarisiz`; oto kod `RP-{yıl}-{id:06d}`; gerçek-zaman olayı `rapor.hazir`.

## Dijital ikiz + kiosk (S15)
İkiz = mevcut verinin üstünde **ince yerleşim katmanı**: `ikiz_dugumleri` yalnız konum
tutar (`x`/`y` yüzde 0–100, `bolge` etiketi; makine başına tek düğüm); canlı durum
`makineler.durum` + `uretim_verileri` penceresinden okunur (`GET /ikiz/durum?saat=`).
Yerleşim yazımı `PUT /ikiz/yerlesim` **replace-all**; gerçek-zaman olayı `ikiz.yerlesim`.
**Kiosk** = kabuksuz `/kiosk` rotası + `kiosk` rolü (yalnız `uretim:oku`) — salt-okunurluk
API garantisi (ADR-0017).

## Abonelik & entitlement (S16)
**Entitlement ≠ RBAC**: izin "bu kullanıcı ne yapabilir", entitlement "bu tenant neyi
satın aldı". Satılabilir birim = **modül** (`MODUL_KATALOGU`, 19 kod — S18: +`entegrasyon` +`dis-portal`; ikiz+kiosk →
`uretim`, ticari pano → `crm`, satınalma → `stok`). Planlar: `deneme` (5 koltuk, tümü) /
`temel` (10) / `profesyonel` (50) / `kurumsal` (sınırsız, tümü). Etkin entitlement =
`modul_haklari` override'ı > planın `moduller` listesi; katalog dışı kod **kapalı**
(fail-closed). Kapalı modül → `403 MODUL_KAPALI` (admin dahil); koltuk aşımı →
`409 KOLTUK_LIMITI` (pasif kullanıcı sayılmaz). Özellik bayrağı = kesitsel/erken-erişim
anahtarı (`mobil-api`, `webhook-onizleme`); modül değildir. Uçlar: `GET /moduller`
(oturum; menü süzgeci), `GET /abonelik` (`abonelik:oku`). ADR-0018.

## Platform admin / control-plane (S17)
Platform yöneticisi **tenant düzleminden ayrık** kimliktir: `public.platform_yonetici` +
JWT tipleri `platform_access`/`platform_refresh` (tenant token'ı platform ucunda ve tersi
**yapısal olarak** 401). Uçlar `/api/v1/platform/*` (`tenant_cozumle` YOK): kimlik,
tenantlar (provizyon senkron; PATCH ad/plan; askıya-al = `tenant.aktif=false` → erişim
ANINDA kesilir; DELETE `onay=slug` şartlı + `DROP SCHEMA CASCADE`), entitlement yazma
(PUT `modul-haklari/{kod}` / `ozellik-bayraklari/{kod}`, `acik:null` = plana dön),
abonelikler, planlar, saglik. **KVKK ihracı**: `tenant_ihraclari` (`kuyrukta →
hazirlaniyor → hazir | basarisiz`) + 202 süreç-içi görev; tenant şeması tabloları
`information_schema` keşfiyle JSON→ZIP → nesne deposu `platform/ihrac/<slug>/<id>/...`
(control-plane öneki, tenant öneki DEĞİL); indirme hazir değilse 409. Tüm platform
yazmaları `platform_denetim_izi`'ne işlenir. ADR-0019.

## Entegrasyon: webhook + API anahtarı (S18)
**Webhook** = outbox'ın dışa akışı. `webhook_abonelikleri` (tenant şeması): `ad`, `url`
(https zorunlu; yalnız yerel test için `http://localhost`), `gizli_anahtar` (`whs_`+43,
imzalama için düz saklanır — API'de maskeli, tam değer yalnız oluşturma/anahtar-yenile
yanıtında bir kez), `olay_turleri` JSONB (katalogdan alt küme; **boş = tümü**), `aktif`.
`webhook_teslimatlari` = olay×abonelik teslimat günlüğü: `durum` (`beklemede → basarili |
yeniden_denenecek → … → basarisiz`), `deneme_sayisi`, `sonraki_deneme_tarihi` (vade
taraması), `yanit_kodu`/`yanit_ozeti`, `govde` (gönderilen zarf v1 anlık görüntüsü),
`dis_anahtar` (tüketici idempotency). İmza: `X-FabrikaOS-Signature: t=<unix>,v1=<hex>` =
HMAC-SHA256(gizli_anahtar, `{t}.{govde}`); backoff 1dk/5dk/30dk/2sa/6sa, 6 deneme →
terminal. Relay ayrı süreç (`scripts/webhook_relay.py`). **Not:** `giden_olaylar.durum`
= `gonderildi` artık "fan-out yapıldı" demektir (teslimat durumu satır başına);
outbox'taki `basarisiz` değeri kullanım dışıdır. Olay kataloğu (8): `is_emri.kapandi`,
`ariza.olustu` (makine arızaya geçişinde kenar-tetikli), `stok.kritik`, `oee.dustu`
(`POST /oee/dusuk-tara`; eşik = `makine.oee_hedefi` yoksa parametre; makine+gün dedup),
`sozlesme.yaklasiyor`, `anomali.tespit`, `kalite.uygunsuzluk`, `isg.kaza`.

**API anahtarı** = 3. taraf (ERP/e-Fatura) erişimi. `api_anahtarlari`: düz anahtar
(`fos_`+43) ASLA saklanmaz — `anahtar_ozet` (SHA-256) ile aranır; `onek` (ilk 12)
görüntü kimliği; `izinler` JSONB kapsamları yalnız beyaz-listeden (`uretim:oku`,
`stok:oku`, `satinalma:oku`); `gecerlilik_tarihi` (null = süresiz), `son_kullanim_tarihi`.
Kimlik `X-API-Anahtar` başlığı + `X-Tenant`; eksik/bilinmeyen/pasif/dolmuş ayrımı
sızdırılmaz (hepsi 401), kapsam yetersiz 403. Dış veri yüzeyi `/api/v1/entegrasyon/*`
salt-okunur: `stok-bakiyeleri`, `satinalma-talepleri` (`?durum=onaylandi` varsayılan),
`uretim-ozeti` (`?gun=`).

## Dış portal (S18)
`kullanici.firma_id` (nullable FK `firmalar`, SET NULL) dış kullanıcıyı CRM firmasına
bağlar. Rol `dis-panel` = yalnız `{dis:erisim}` — iç uçlarda yapısal 403. `/api/v1/dis/*`
(`modul_gerekli("dis-portal")`): firma süzgeci **dependency'de** zorlanır
(`dis_firma_kullanici`); başka firmanın talebi listede yok + ID ile 404; firmasız
kullanıcı (admin dahil) 403. Portal talebi iç `talepler` tablosuna yazar (TL- kod +
durum makinesi + `talep.olusturuldu` gerçek-zamanı aynen); dış DTO iç alanları
(atama, firma_id) sızdırmaz. Modüller `entegrasyon` + `dis-portal` yalnız
deneme/kurumsal planlarında; webhook uçları `entegrasyon` VEYA `webhook-onizleme`
bayrağıyla açılır (S16 tüketimi). ADR-0020.

## Bildirim Merkezi + SLA + skor/harita (S-VB / ADR-0021)
**Bildirim** = kişi-hedefli, tenant içi uygulama-içi bildirim. `bildirimler`:
`kullanici_id` (CASCADE), `giden_olay_id` (kaynak outbox olayı; nullable),
`olay_turu` (denorm), `baslik`/`govde` (TR referans metin), `veri` JSONB
(derin-bağlantı `{kaynak_tur, kaynak_id}`), `onem` (`bilgi`/`uyari`/`kritik`),
`okundu`+`okundu_tarihi`. **`UNIQUE(kullanici_id, giden_olay_id)`** = üretici
idempotency (ikinci tarama çift bildirim üretemez). `bildirim_tercihleri`:
kullanıcı × olay türü `uygulama_ici`/`eposta` (kayıt yoksa varsayılan: içi açık,
e-posta kapalı). `bildirim_imleci`: üreticinin tek satırlık outbox yüksek-su-işareti
(`son_islenen_olay_id`). Üretici ayrı süreçtir (`scripts/bildirim_uretici.py`);
hedefleme saf kural tablosu (`bildirim/hedefleme.py`): izne-göre (ör. `stok.kritik`
→ `stok:oku` sahipleri) veya kişi-hedefli (`rapor.hazir` → oluşturan). Uçlar
`/bildirimler*` + `/bildirim-tercihleri` **kişisel yüzeydir** (oturum yeter; izin ve
modül kapısı yok); süzgeç repository imzasında zorlanır. `duyuru.yeni` artık outbox'a
da yazılır.

**SLA**: `is_emirleri.hedef_tarih` + `talepler.hedef_tarih` (nullable; boş = takip yok).
`POST /is-emirleri/sla-tara` (`isemri:yaz`) + `POST /talepler/sla-tara` (`talep:yaz`)
kenar-tetikli `sla.asildi` outbox olayı üretir; **dedup outbox'tan** sorgulanır
(`core/sla.py` — kaynak başına bir kez). Webhook kataloğu 8 → **9** (`sla.asildi`).
Talep SLA'sında yalnız `acik`/`inceleniyor` taranır (`cozuldu` karşılanmış sayılır).

**Operatör eşleştirme**: `POST /tahmin/operator-eslesme` (`ai:oku`, modül `ai`) —
kural-tabanlı saf skor (0.5 departman + 0.3 geçmiş kapanış + 0.2 müsaitlik), kesin
sıralı, model artefaktsız.

**Tedarikçi skoru**: `GET /firmalar/{id}/skor` (`crm:oku`) = `40·kalite_gecme +
30·sozlesme_uyumu + 30·talep_cozum` (0–100); sinyalsiz bileşen nötr 0.5 +
`yetersiz_veri` listesi; `zamaninda_teslim` S25'te dolar. Bağlantı kolonları:
`malzemeler.tedarikci_firma_id` (ana tedarikçi) + `kalite_kontrolleri.malzeme_id`
(giriş kontrolü) — ikisi de nullable FK.

**Coğrafi harita**: `makineler.enlem`/`boylam` (nullable; ±90/±180 doğrulamalı);
`PATCH /makineler/{id}` (ad/oee_hedefi/koordinat) eklendi; `/ikiz/durum` koordinat
taşır; FE `/ikiz` "Harita" sekmesi (react-leaflet + OSM). Takvim: `/bakim-planlari`
"Takvim" sekmesi (bakım vadeleri + onaylı izinler; FE-only).
