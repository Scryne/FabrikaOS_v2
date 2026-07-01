# ADR-0011: Stok & Satınalma — tutulan bakiye + kenar-tetikli kritik + çok-kalemli talep/onay (görev ayrımı)

Durum: Kabul
Tarih: 2026-06-30

## Bağlam
Faz 2 / S9 çekirdeğin üzerine çok-kiracılı, RBAC-korumalı bir **Stok & Satınalma** modülü
ekler: malzeme kartı + stok hareketi, kritik-eşik uyarısı, çok-kalemli satınalma talebi +
onay akışı. Kabul kriterleri: (1) bakiye **doğru** (eşzamanlı hareketlerde bile), (2) kritik
eşiğe düşüş **uyarı tetikler**, (3) onaylama yetkisi talep oluşturmadan **ayrı** (görev
ayrımı / segregation of duties).

Mevcut altyapı: şema-başına-tenant + `search_path` (ADR-0003), Alembic iki-ağaç fan-out
(ADR-0004), RBAC izin/rol kataloğu (ADR-0005), transactional outbox + saf durum makinesi
deseni (ADR-0007), Redis pub/sub gerçek-zaman (ADR-0009). S9 bu desenleri yeniden kullanır.

## Karar
- **Tutulan bakiye (`Malzeme.mevcut_miktar`) + `FOR UPDATE` satır kilidi.** Bakiye her
  hareket türetilerek (SUM) değil, malzeme satırında **tutulur**; her `StokHareketi` servis
  katmanında malzemeyi `FOR UPDATE` ile kilitli getirip günceller → eşzamanlı hareketler seri
  hâle gelir, çift güncelleme olmaz. Hızlı okuma (liste/kritik kontrolü tek satır) + append-only
  `stok_hareketleri` denetim izini birlikte sağlar. `bakiye_sonrasi` her harekette snapshot'lanır.
  `duzeltme` türü `miktar`'ı **mutlak yeni bakiye** olarak yorumlar (fiziksel sayım düzeltmesi).
- **Kenar-tetikli `stok.kritik` olayı (transactional outbox).** Olay yalnız bakiye **kritik
  eşiğin üstünden altına ilk geçtiğinde** yayınlanır (kenar tetik; seviye değil) → eşik
  altındayken her hareket gürültü üretmez. Olay, hareketi yazan iş ile **aynı transaction'da**
  `giden_olaylar` outbox'ına yazılır (ADR-0007) → atomik; ileride webhook (S18) tüketebilir.
  `govde` JSON-native (Decimal → `float`; JSONB Decimal'i serialize etmez).
- **Çok-kalemli satınalma talebi + saf durum makinesi (görev ayrımı).** `SatinalmaTalebi`
  (n `SatinalmaTalebiKalemi`); yaşam döngüsü saf, DB'siz, kapsamlı birim testli
  `talep_durum.py`: `taslak → onay_bekliyor → onaylandi | reddedildi` (+ her aşamada `iptal`);
  terminal durumlardan çıkış yok. `onayla`/`reddet` uçları **`satinalma:onay`** iznini ister;
  `oluştur`/`gönder`/`iptal` **`satinalma:yaz`**. `depo` rolü yaz ama onay iznine **sahip
  değil** → görev ayrımı canlı testli (`test_onay_ayri_izin_403`). `reddedildi` `red_nedeni`
  zorunlu. Talep kodu insan-okur: `ST-{yıl}-{id:06d}` (id bilinince kalıcı koda yazılır).
- **Opsiyonel `Idempotency-Key` (stok hareketi).** Başlık verilirse `stok_hareketleri`nde
  nullable-unique `idempotency_anahtari` ile çift-gönderim engellenir; ikinci istek mevcut
  hareketi döndürür (bakiye tek kez değişir). Genel middleware'e çıkarmak ileride mümkün (seam).
- **Talep ↔ stok ayrık.** Onaylanan talep otomatik stok girişi yapmaz; mal kabul / sipariş
  bağlama Faz ilerisine bırakıldı (YAGNI). Para değeri türetilmiş: `tahmini_toplam` kalem
  `miktar × tahmini_birim_fiyat` toplamıdır (kalıcı kolon değil).

## Sonuçlar
- (+) Bakiye doğruluğu (`FOR UPDATE`), kenar-tetikli kritik (bir kez), idempotency, tenant
  izolasyonu ve `satinalma:onay` 403 senaryoları entegrasyon testli ve kalıcı (S9 ~29 test).
- (+) OEE / üretim hattı S9'dan etkilenmedi; `stok.kritik` outbox olayı webhook (S18) için hazır.
- (+) Miktar `Numeric(18,3)` (Decimal aritmetik), para `Numeric(18,2)`; cevap DTO'ları `float`.
- (−) Idempotency yalnız sıralı çift-gönderimi test kapsar; eşzamanlı aynı anahtar unique kısıtla
  sert-garanti (ikinci yazım IntegrityError) — zarif "mevcut döndür" ileride eklenebilir.
- (−) Kritik kenar tetik yalnız "üstten alta ilk geçiş"te yayınlar; başlangıçta zaten eşik
  altında oluşturulan malzeme ilk çıkışta olay üretmez (yapısal — `/stok/kritik` yine listeler).
- (−) Talep-stok ayrık olduğundan onay sonrası stok etkisi elle yapılır (mal kabul Faz ilerisi).

## Notlar
- Migration `a3d9f1c52e84` (down `f3a9c1d72b84`); hypertable yok (ilişkisel, düşük hacim);
  `public` + ≥2 tenant şemasında fan-out up/down testli (`test_s9_migration.py`).
- İzin kodları (`stok:oku/yaz`, `satinalma:oku/yaz/onay`) katalogda S2'den beri vardı; S9
  yalnız görev-ayrımını canlı gösteren `depo` + `satinalma-onaylayan` **rollerini** ekledi.
