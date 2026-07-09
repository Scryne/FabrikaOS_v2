# ADR-0018: Abonelik, Entitlement & Feature Flag — modül modül satılabilir ürün

Durum: Kabul
Tarih: 2026-07-09

## Bağlam
Faz 4 / S16: ürünün modül modül lisanslanması. Kabul kriterleri: kapalı modüle erişim
backend + UI'da engellenir, koltuk (seat) limiti aşımı engellenir, entitlement değişimi
anında etkili olur, bypass için güvenlik testi vardır.

Control-plane'de `tenant` + `abonelik` (plan_kodu string) S2'den beri vardı; plan
tanımı ve modül hakkı kavramı yoktu. Tenant çözümleme zaten her istekte public'e
gidiyor (ADR-0003), RBAC izinleri tenant şemasında (ADR-0005).

## Karar
- **Entitlement ≠ RBAC.** İzin (RBAC) "bu kullanıcı ne yapabilir", entitlement "bu
  tenant neyi satın aldı" sorusudur; iki katman bağımsız zorlanır. Kapalı modülde
  **admin dahil** herkes `403 MODUL_KAPALI` alır.
- **Satılabilir birim = modül; katalog kodda.** `MODUL_KATALOGU` (17 modül),
  `OZELLIK_KATALOGU` (feature flag'ler), `PLAN_KATALOGU` (deneme 5 koltuk / temel 10 /
  profesyonel 50 / kurumsal sınırsız) `app/control_plane/moduller.py`'de tek kaynak.
  İkiz+kiosk `uretim`'e, ticari pano `crm`'e, satınalma `stok`'a bağlıdır (menü
  bölümleriyle hizalı; ayrı satılmaz). Kimlik/kullanıcı/rol/abonelik uçları çekirdektir.
- **Veri modeli (public):** `planlar` (kod uq + `moduller`/`ozellikler` JSONB listeleri +
  `koltuk_limiti` null=sınırsız) + tenant-başına istisna tabloları `modul_haklari` ve
  `ozellik_bayraklari` (uq tenant+kod). `abonelik.plan_kodu` → FK `planlar.kod`.
  **JSONB liste, ilişkisel plan_modul tablosu değil**: plan tanımı atomik değişen küçük
  bir değer nesnesidir; join maliyeti ve migration çilesi almaya değmez. Migration
  statik seed yazar; provizyon her koşuda katalogla **upsert-eşitler** (katalog evrimi
  yeni migration istemez).
- **Etkin entitlement = override > plan; bilinmeyen kod KAPALI (fail-closed).** Saf
  hesap `entitlement.py`'de (birim testli), sorgular `entitlement_service.py`'de.
- **Zorlama router seviyesinde `modul_gerekli(kod)` dependency'siyle** (19 modül
  router'ı). Plan + override **istek başına taze sorgulanır — önbellek YOK**: değişim
  bir sonraki istekte etkilidir (kabul kriteri). Redis önbelleği bilinçli ertelendi;
  sorgular indeksli ve ucuz, ölçüm gerekirse S19'da eklenir.
- **Koltuk limiti kullanıcı oluşturmada zorlanır:** `public.tenant` satırı `FOR UPDATE`
  kilidiyle eşzamanlı oluşturmalar serileştirilir; aktif kullanıcı sayısı ≥ limit →
  `409 KOLTUK_LIMITI`. Pasif kullanıcı koltuk saymaz (pasifleştirme koltuk açar).
- **Uçlar:** `GET /moduller` yalnız oturum ister (menü süzgeci her kullanıcıya lazım;
  yalnız modül adı/açıklık sızar — menünün zaten gösterdiği bilgi). `GET /abonelik`
  (plan + dönem + koltuk kullanım + matris) yeni `abonelik:oku` iznine bağlı.
- **Entitlement YAZMA API'si S17'ye bırakıldı** (platform admin paneli). S16'da
  değişiklik control-plane servis fonksiyonları + `scripts/entitlement_ayarla.py` CLI
  ile yapılır; platform kimliği/paneli olmadan tenant-dışı yazma ucu açılmaz.
- **Frontend:** `useModuller` → menü süzgeci (kapalı modül menüde yok) + `ModulKapisi`
  rota kapısı (doğrudan URL → upsell boş durumu + `/abonelik` CTA). UI süzgeci
  **fail-open** (veri gelmeden/uçta hata varsa gizlemez) — güvenlik backend'dedir,
  UI süzgeci kozmetiktir. `/abonelik` ekranı: plan kartı + koltuk progress + hat renkli
  modül matrisi + "deneysel" özellik rozetleri.
- **Feature flag'ler modül değildir:** kesitsel/erken-erişim anahtarları (`mobil-api`,
  `webhook-onizleme`). S16 mekanizmayı + görünürlüğü kurar; tüketimleri ilgili
  sprintte (S18/FAZ 7) gelir.

## Sonuçlar
- Ürün modül modül satılabilir; plan değişimi/override anında etkilidir (testli).
- Test fixture tenant'ları (alfa/beta) `kurumsal` planda provizyonlanır — mevcut süit
  koltuk/entitlement limitine takılmaz; limit senaryoları `temel` planlı üçüncü
  tenant'la (gamma16) test edilir.
- Her modül isteğine 2 ek public sorgusu (plan + override) eklendi; kabul edilebilir,
  gerekirse S19'da ölçülüp önbelleklenir (anında-etki şartı Redis invalidasyonu ister).
- S17 platform paneli bu servis fonksiyonlarının üstüne yalnız HTTP/RBAC katmanı koyar.
