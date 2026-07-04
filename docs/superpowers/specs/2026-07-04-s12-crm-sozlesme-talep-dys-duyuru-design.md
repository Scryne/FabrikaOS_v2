# S12 — CRM / Sözleşme / Talep + DYS + Duyuru + Ticari Pano (Tasarım)

**Faz 2 / Sprint 12.** Amaç: ticari (CRM) çekirdek + doküman yönetim sistemi (DYS,
sürümlü, nesne depolamada) + duyuru/bildirim + odaklı ticari özet panosunu, mevcut
çekirdek (tenant izolasyonu, RBAC, outbox, gerçek-zaman) üzerine, tam izole ve korumalı
biçimde eklemek.

## Kapsam kararları
- **DYS depolama:** Pluggable `NesneDepo` soyutlaması. Gerçek/dev sürücü = MinIO/S3
  (`minio` Python SDK; `.env.example`'daki `MINIO_*` değişkenlerine birebir oturur).
  Testler için `BellekNesneDepo` (bellek-içi sözlük). Tenant izolasyonu **anahtar öneki**
  ile: `tenant_<slug>/belge/<belge_id>/<surum>/<dosya>`. Senkron SDK çağrıları async
  uçlarda `asyncio.to_thread` ile sarılır (provizyon deseni).
- **Modül panoları:** Odaklı **ticari özet** — `GET /ticari/ozet` (sayaçlar + yaklaşan
  sözleşmeler + son duyurular) + `TicariPano` ekranı. Kapsam şişmesi yok.

## Modüller (tenant şeması)
| Modül | Tablolar | REST kökü | İzinler |
|---|---|---|---|
| `crm` | `firmalar`, `ortaklar` | `/firmalar`, `/ortaklar` | `crm:oku`, `crm:yaz` |
| `sozlesme` | `sozlesmeler` | `/sozlesmeler` | `sozlesme:oku`, `sozlesme:yaz` |
| `talep` | `talepler` | `/talepler` | `talep:oku`, `talep:yaz` |
| `dys` | `belgeler`, `belge_surumleri` | `/belgeler` | `dys:oku`, `dys:yaz` |
| `duyuru` | `duyurular` | `/duyurular` | `duyuru:oku`, `duyuru:yaz` |

Yeni izinler: `crm:yaz`, `sozlesme:oku`, `sozlesme:yaz`, `talep:oku`, `duyuru:oku`,
`duyuru:yaz` (`crm:oku`, `talep:yaz`, `dys:oku`, `dys:yaz` katalogda vardı). Yeni roller:
`crm` (crm+sozlesme+talep yaz), `dokuman` (dys), `duyuru` (duyuru yaz). `izleyici` tüm
`:oku`'ları otomatik alır.

## Veri modeli (öz)
- **Firma** — `ad`, `tip` (musteri/tedarikci/her_ikisi), `vergi_no`, `vergi_dairesi`,
  `telefon`, `eposta`, `adres`, `il`, `sektor`, `web_sitesi`, `sorumlu_kullanici_id?`,
  `aktif`, `aciklama`.
- **Ortak** (firma ilgili kişisi) — `firma_id`, `ad_soyad`, `unvan`, `telefon`, `eposta`,
  `birincil`, `aktif`, `aciklama`.
- **Sozlesme** — oto kod `SZ-{yıl}-{id:06d}`; `firma_id`, `baslik`, `tur`
  (satis/alis/hizmet/nda/kira/diger), `baslangic_tarihi`, `bitis_tarihi`, `tutar`,
  `para_birimi`, `durum` (durum makinesi), `sorumlu_kullanici_id?`, `yaklasim_bildirildi`,
  `aciklama`.
- **Talep** — oto kod `TL-{yıl}-{id:06d}`; `firma_id?`, `baslik`, `aciklama`, `tur`
  (teklif/destek/sikayet/bilgi/diger), `oncelik` (dusuk/orta/yuksek), `durum`
  (durum makinesi), `atanan_kullanici_id?`, `talep_eden_kullanici_id?`, `talep_eden_ad`.
- **Belge** — oto kod `BLG-{yıl}-{id:06d}`; `ad`, `kategori`, `aciklama`, `guncel_surum`,
  `aktif`, `olusturan_kullanici_id?`.
- **BelgeSurumu** — `belge_id`, `surum_no` (uq: belge_id+surum_no), `dosya_adi`,
  `icerik_tipi`, `boyut`, `nesne_anahtari`, `yukleyen_kullanici_id?`, `aciklama`.
- **Duyuru** — oto kod `DUY-{yıl}-{id:06d}`; `baslik`, `icerik`, `onem`
  (bilgi/uyari/kritik), `yayinda`, `yayin_tarihi`, `bitis_tarihi?`, `hedef_departman`,
  `olusturan_kullanici_id?`.

## Durum makineleri (saf, birim testli)
- **Sözleşme:** `taslak → aktif → (sonlandi | feshedildi)` + her aktif olmayan-terminal
  aşamadan `iptal`. Terminal: `sonlandi`, `feshedildi`, `iptal`.
- **Talep:** `acik → inceleniyor → cozuldu → kapandi`; `cozuldu → inceleniyor` (yeniden aç);
  `acik|inceleniyor → iptal`. Terminal: `kapandi`, `iptal`.

## Domain olayları
- **`sozlesme.yaklasiyor`** — outbox (dayanıklı). `POST /sozlesmeler/yaklasanlari-tara`
  (zamanlayıcı/beat çağırır) `aktif` + bitişine ≤ eşik gün kalan + `yaklasim_bildirildi=false`
  sözleşmeler için **kenar-tetikli** olarak bir kez olay yazar (S9 `stok.kritik` deseni).
- **Gerçek-zaman (best-effort):** `crm.firma`, `sozlesme.durum`, `talep.durum`,
  `talep.olusturuldu`, `duyuru.yeni`, `dys.belge`.

## Nesne depolama izolasyonu
Anahtar öneki tenant-slug ile başlar; bir sürücü örneği bucket paylaşsa bile tenant'lar
önekle ayrışır. Sürüm append-only: yeni yükleme `guncel_surum+1` ve yeni bir
`belge_surumleri` satırı üretir; eski sürümler silinmez (denetlenebilirlik).

## İzolasyon + RBAC (DoD)
Her uç `tenant_cozumle` + `izin_gerekli(...)`. İzolasyon: A tenant'ında oluştur, B'de sorgula
→ 404. Görev ayrımı gerektiren onay yok (CRM/sözleşme/talep tek yaz izniyle yönetilir;
sözleşme/talep durum geçişleri `*:yaz`).

## Ertelenenler
- `sozlesme.yaklasiyor` teslimatı (webhook relay + imza + retry) → S18.
- Beat/zamanlayıcı ile otomatik tarama → S14/operasyon (S12 uç sağlar).
- MinIO mTLS/politika sertleştirme, imzalı indirme URL'leri → Faz 5.
