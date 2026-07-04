# ADR-0014: CRM / Sözleşme / Talep + DYS (nesne depolama) + Duyuru + Ticari Pano

Durum: Kabul
Tarih: 2026-07-04

## Bağlam
Faz 2 / S12, çekirdeğin üzerine ticari (satış/CRM) çekirdeği, **DYS** (Doküman Yönetim
Sistemi — sürümlü belge) ve **Duyuru**/bildirim modüllerini ekler; ayrıca "modül panosu"
kabul kriteri için odaklı bir **ticari özet** panosu sağlar. DYS, dosya içeriğini ilişkisel
DB dışında bir **nesne deposunda** tutmayı gerektirir (docker-compose'da MinIO hazır).

Mevcut altyapı yeniden kullanılır: şema-başına-tenant + `search_path` (ADR-0003), Alembic
fan-out (ADR-0004), RBAC (ADR-0005), transactional outbox + saf durum makinesi (ADR-0007),
kenar-tetikli domain olayı (ADR-0011 `stok.kritik`), Redis pub/sub gerçek-zaman (ADR-0009).

## Karar
- **CRM.** `Firma` (müşteri/tedarikçi/her_ikisi; `tip` beyaz-liste) + `Ortak` (firma ilgili
  kişisi, `birincil` ana kontak). Onay/durum makinesi yok; okuma `crm:oku`, yazma `crm:yaz`.
- **Sözleşme.** `Sozlesme` firmaya FK; oto kod `SZ-{yıl}-{id:06d}`; saf durum makinesi
  (`sozlesme/durum.py`: `taslak → aktif → sonlandi|feshedildi` + `iptal`, terminalden çıkış
  yok), geçiş `FOR UPDATE`. **`sozlesme.yaklasiyor`** domain olayı **kenar-tetiklidir**:
  `POST /sozlesmeler/yaklasanlari-tara` (zamanlayıcı/beat çağırır), aktif + bitişine ≤ eşik
  gün kalan + `yaklasim_bildirildi=false` sözleşmeler için **sözleşme başına bir kez** outbox
  olayı yazar (S9 `stok.kritik` deseni). Teslimat (webhook relay) S18'e bırakıldı.
- **Talep.** `Talep` (teklif/destek/şikayet/bilgi); opsiyonel `firma_id` + `atanan_kullanici_id`;
  oto kod `TL-{yıl}-{id:06d}`; saf durum makinesi (`acik → inceleniyor → cozuldu → kapandi`,
  `cozuldu → inceleniyor` yeniden aç, `+iptal`), geçiş `FOR UPDATE`. Dış self-servis portal
  (S18) da bu kayda talep yazacaktır. Okuma `talep:oku`, yazma `talep:yaz`.
- **DYS — nesne depolama soyutlaması.** `Belge` (mantıksal doküman) + `BelgeSurumu`
  (append-only sürüm). Dosya içeriği DB'de değil **nesne deposunda**; DB yalnız üstveri +
  `nesne_anahtari` tutar. Soyutlama `dys/depolama.py` `NesneDepo` protokolü; iki uygulama:
  `MinioNesneDepo` (MinIO/S3, `minio` SDK — `.env` `MINIO_*`) ve `BellekNesneDepo` (testler).
  **Tenant izolasyonu anahtar önekiyle:** `tenant_<slug>/belge/<belge_id>/<surum>/<dosya>` →
  bir bucket paylaşılsa bile tenant'lar önekle ayrışır. Senkron SDK çağrıları `asyncio.to_thread`
  ile sarılır (event loop bloklanmaz; provizyon deseni). Yükleme yeni sürüm üretir
  (`guncel_surum+1`), eski sürümler silinmez (denetlenebilirlik). `nesne_anahtari` API'de
  **açığa çıkmaz**. Okuma/indirme `dys:oku`, yükleme `dys:yaz`.
- **Duyuru.** `Duyuru` (önem: bilgi/uyari/kritik); oto kod `DUY-{yıl}-{id:06d}`; `yayinla`
  ile yayına alınır ve **`duyuru.yeni`** gerçek-zaman olayı üretir (bağlı istemciler bildirim
  alır); `kaldir` ile yayından alınır. Okuma `duyuru:oku`, yazma/yayın `duyuru:yaz`.
- **Ticari pano.** `GET /ticari/ozet` (`crm:oku`): firma/aktif sözleşme/yaklaşan sözleşme/
  açık talep/yayınlı duyuru sayaçları + yaklaşan sözleşme listesi + son yayınlanan duyurular.
- **RBAC.** Yeni izinler: `crm:yaz`, `sozlesme:oku/yaz`, `talep:oku`, `duyuru:oku/yaz`
  (`crm:oku`, `talep:yaz`, `dys:oku/yaz` katalogda vardı). Yeni roller: `crm`
  (crm+sözleşme+talep yaz), `dokuman` (dys), `duyuru`. `izleyici` tüm `:oku`'ları otomatik alır.

## Sonuçlar
- (+) Sürümlü doküman yükle/indir + tenant-izole nesne öneki, sözleşme durum makinesi +
  kenar-tetikli `sozlesme.yaklasiyor` (bir kez), talep yaşam döngüsü, duyuru realtime,
  ticari özet ve migration fan-out up/down entegrasyon testli ve kalıcı (+57 backend → 283).
- (+) DYS depolama soyutlaması pluggable: CI/testler altyapısız (`BellekNesneDepo`), dev/prod
  MinIO/S3. Somut SDK `NesneDepo` ardında → değiştirilebilir.
- (+) Üretim/OEE hattı ve diğer modüller S12'den **etkilenmez**; yeni modüller ayrıktır.
- (−) `sozlesme.yaklasiyor` taraması bir uçtur; otomatik zamanlama (Celery beat) S14/operasyona
  bırakıldı (YAGNI; uç hazır).
- (−) MinIO imzalı indirme URL'leri, mTLS ve bucket politikası sertleştirme Faz 5'e ertelendi;
  şu an indirme API üzerinden akar (RBAC korumalı).
- (−) Belge içeriğinde tam-metin arama / virüs tarama kapsam dışı (sonraki iterasyon).

## Notlar
- Migration `e1f4a2c3b567` (down `d5c8e1f0a927`); 7 tablo (`firmalar`, `ortaklar`,
  `sozlesmeler`, `talepler`, `belgeler`, `belge_surumleri`, `duyurular`), hypertable/CAGG yok;
  `public` + ≥2 tenant şemasında fan-out up/down testli (`test_s12_migration.py`).
- Uçlar: `/firmalar`, `/ortaklar`, `/sozlesmeler` (+`/{id}/durum`, `/yaklasan`,
  `/yaklasanlari-tara`), `/talepler` (+`/{id}/durum`), `/belgeler`
  (+`/{id}/surumler` yükle/liste, `/{id}/surumler/{no}/indir`), `/duyurular`
  (+`/{id}/yayinla|kaldir`), `/ticari/ozet`. Realtime: `crm.firma`, `sozlesme.durum`,
  `sozlesme.yaklasiyor`, `talep.olusturuldu`, `talep.durum`, `dys.belge`, `duyuru.yeni`.
- Yeni bağımlılık: `minio>=7.2` (S3 uyumlu nesne depolama SDK).
