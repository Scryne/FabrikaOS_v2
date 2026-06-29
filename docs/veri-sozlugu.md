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
| JWT | JSON Web Token; access (kısa) + refresh (rotasyonlu) |
| Refresh rotasyonu | Yenilemede eski refresh'i iptal edip yeni çift üretme (Redis iptal listesi) |
| RPO / RTO | Kabul edilebilir veri kaybı / kurtarma süresi (DR) |

## Identifier sözlüğü (tablo/model/kolon)
| Kavram | Identifier (tekil / çoğul) |
|---|---|
| Makine | `makine` / `makineler` |
| Üretim verisi | `uretim_verisi` / `uretim_verileri` |
| İş emri | `is_emri` / `is_emirleri` |
| Bakım | `bakim` / `bakim_planlari` |
| Arıza | `ariza` / `arizalar` |
| Malzeme | `malzeme` / `malzemeler` |
| Stok hareketi | `stok_hareketi` / `stok_hareketleri` |
| Satınalma talebi | `satinalma_talebi` / `satinalma_talepleri` |
| Kullanıcı | `kullanici` / `kullanicilar` |
| Rol / İzin | `rol` / `roller`, `izin` / `izinler` |
| Personel | `personel` / `personeller` |
| İzin talebi (İK) | `izin_talebi` / `izin_talepleri` |
| İş kazası | `is_kazasi` / `is_kazalari` |
| Risk değerlendirme | `risk_degerlendirme` / `risk_degerlendirmeleri` |
| Kalite kontrol | `kalite_kontrol` / `kalite_kontrolleri` |
| Uygunsuzluk (CAPA) | `uygunsuzluk` / `uygunsuzluklar` |
| Enerji tüketim | `enerji_tuketim` / `enerji_tuketimleri` |
| Firma | `firma` / `firmalar` |
| Sözleşme | `sozlesme` / `sozlesmeler` |
| Talep | `talep` / `talepler` |
| Belge (DYS) | `belge` / `belgeler` |
| Duyuru | `duyuru` / `duyurular` |
| Denetim izi (audit) | `denetim_izi` |
| Tenant | `tenant` / `tenantlar` |
| Abonelik | `abonelik` / `abonelikler` |

## Ortak kolonlar
`olusturma_tarihi`, `guncelleme_tarihi`, `olusturan_id`, `durum`, `<x>_id` (FK).

## İzin formatı
`modul:islem` → `uretim:oku`, `uretim:yaz`, `uretim:sil`, `isemri:yaz`, `stok:oku`,
`satinalma:onay`, `platform-admin`, `dis-panel`.
