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
| Denetim izi (audit) | `denetim_izi` |
| Tenant | `tenant` / `tenantlar` |
| Abonelik | `abonelik` / `abonelikler` |

## Ortak kolonlar
`olusturma_tarihi`, `guncelleme_tarihi`, `olusturan_id`, `durum`, `<x>_id` (FK).

## İzin formatı
`modul:islem` → `uretim:oku`, `uretim:yaz`, `uretim:sil`, `isemri:yaz`, `stok:oku`,
`satinalma:onay`, `isg:oku`, `isg:yaz`, `ik:oku`, `ik:yaz`, `ik:onay`, `crm:oku`, `crm:yaz`,
`sozlesme:oku`, `sozlesme:yaz`, `talep:oku`, `talep:yaz`, `dys:oku`, `dys:yaz`, `duyuru:oku`,
`duyuru:yaz`, `platform-admin`, `dis-panel`. Görev ayrımı: `satinalma:onay` ve `ik:onay`
yalnız onaylayan rollerdedir.

## Nesne depolama (DYS)
Belge içeriği ilişkisel DB'de değil **nesne deposunda** (MinIO/S3) tutulur; tenant izolasyonu
anahtar önekiyle: `tenant_<slug>/belge/<belge_id>/<surum>/<dosya>`. Soyutlama `NesneDepo`
(`MinioNesneDepo` gerçek + `BellekNesneDepo` test). Sürümler append-only.
