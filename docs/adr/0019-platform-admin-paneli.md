# ADR-0019: Platform Admin Paneli — control-plane kimliği ve tenant yaşam döngüsü

Durum: Kabul
Tarih: 2026-07-10

## Bağlam
Faz 4 / S17: control-plane'in API + panelle yönetilmesi. Kabul kriterleri: panelden
yeni tenant dakikalar içinde provizyonlanır, askıya alma erişimi keser, ihraç tenant
verisini eksiksiz dışa aktarır (KVKK). S16 entitlement yazma API'sini bilinçli olarak
bu sprinte bırakmıştı (ADR-0018): platform kimliği olmadan tenant-dışı yazma ucu
açılmayacaktı. `platform-admin` tenant izin kataloğunda YOKTUR (tenant-rbac-conventions
bunu belgeli istisna sayar: `/api/v1/platform/*` tenant'tan bağımsızdır).

## Karar
- **Ayrı kimlik düzlemi: `public.platform_yonetici`.** Platform operatörü hiçbir
  tenant şemasına bağlı değildir; tenant `Kullanici`/RBAC'i ile kesişmez. Rol/izin
  granülaritesi YOK — tüm platform yöneticileri eşittir (ihtiyaç doğarsa S23'te
  genişletilir). İlk hesap CLI ile açılır (`scripts/platform_yonetici_olustur.py`,
  eposta-idempotent); migration'a parola gömülmez.
- **Aynı JWT altyapısı, ayrı token tipleri:** `platform_access` / `platform_refresh`.
  `jwt.coz(token, beklenen_tip)` tip kontrolü sayesinde tenant token'ı platform
  ucunda, platform token'ı tenant ucunda **yapısal olarak** 401'dir (testli).
  Rotasyonlu refresh + Redis iptal listesi + `giris:platform:<ip>` rate limit aynen
  yeniden kullanılır. `tenant_slug` claim'i platform token'larında inert `"platform"`
  sabitidir.
- **Uçlar `/api/v1/platform/*`** (`mevcut_platform_yonetici` korumalı; `tenant_cozumle`
  YOK): kimlik (token/yenile/cikis/ben) · tenantlar (liste+arama+koltuk kullanımı /
  detay+entitlement matrisi / POST provizyon / PATCH ad+plan / askıya-al / aktifleştir /
  DELETE) · entitlement yazma (PUT modul-haklari/{kod}, PUT ozellik-bayraklari/{kod};
  `acik: null` = override kaldır) · abonelikler · planlar · saglik · ihraclar.
- **Provizyon senkron beklenir** (`tenant_provizyonla` idempotent, saniyeler sürer);
  202+iş takibi karmaşasına değmez. Süre büyürse (çok migration'lı gelecek) S19'da
  202 + durum kolonuna yükseltilir. Var olan slug → 409.
- **Askıya alma = `tenant.aktif=False`.** `tenant_cozumle` aktif olmayan tenant'ı
  404'lediği ve hiçbir katmanda önbellek olmadığı için erişim (giriş dahil) bir
  sonraki istekte kesilir; aktifleştirme simetriktir.
- **Silme geri dönüşsüzdür ve çift korumalıdır:** gövdedeki `onay` alanı slug ile
  birebir eşleşmek zorunda (422), panelde ayrıca slug-yazarak-onay modalı (GitHub
  deseni). `DROP SCHEMA tenant_<slug> CASCADE` + public satır (FK CASCADE: abonelik/
  haklar/bayraklar/ihraçlar). Denetim kaydı silmeden ÖNCE yazılır.
- **KVKK ihracı = S14 rapor deseninin control-plane aynası:** `tenant_ihraclari`
  public tablosu (`kuyrukta→hazirlaniyor→hazir|basarisiz`) + 202 + süreç-içi async
  görev. **Eksiksizlik keşfe bağlıdır:** tenant şemasındaki tablolar
  `information_schema`'dan bulunur → gelecek modül tabloları otomatik kapsanır;
  public kayıtları (tenant/abonelik/haklar/bayraklar) ayrıca eklenir. Çıktı: tablo
  başına JSON + manifest içeren tek ZIP → `NesneDepo`'ya **`platform/ihrac/...`**
  anahtarıyla (tenant `tenant_<slug>/...` önekinin dışında: artefakt control-plane'e
  aittir; tenant silinse de FK CASCADE kaydı düşürür). İndirme `hazir` değilse 409.
- **Platform denetim izi `public.platform_denetim_izi`:** tenant `denetim_izi`'nin
  aynası; provizyon/güncelleme/askı/silme/entitlement/ihraç/giriş buraya işlenir
  (kim-ne-ne zaman + request_id + IP).
- **Frontend: aynı SPA içinde `/platform/*` rotaları, ayrı düzlem.** Ayrı auth store +
  istemci (X-Tenant başlığı YOK, refresh ayrı localStorage anahtarında, 401→
  `/platform/kimlik/yenile` single-flight) — tenant oturumuyla yan yana yaşayabilir.
  Kimlik: turuncu `#f97316` "platform" hattı + kabukta kalıcı **PLATFORM filigran
  çipi** (yanlış düzlemde işlem riskine karşı). `admin.fabrikaos.com` ayrı subdomain
  servisi Faz 5 operasyon işidir (Traefik kuralı aynı bundle'ı servis eder); kod
  düzeyinde düzlem ayrımı bugünden kuruldu.
- **DTO adları platforma özgü:** `PlatformModulDurumDTO`/`PlatformOzellikDurumDTO` —
  abonelik modülü DTO'larıyla ad çakışması openapi-typescript üretimini bozuyordu.

## Sonuçlar
- Faz 4'ün "platform admin" ayağı tamam: tenant aç/kapa/planla/ihrâç et — panelden.
- S16'nın CLI'ları (entitlement_ayarla) artık ikincil; API + panel birincil yol.
- Platform düzlemi WS/gerçek-zaman içermez (bilinçli sadelik); ihraç durumu kısa
  aralıklı yoklamayla izlenir. Gerekirse S19 gözlemlenebilirlik sprintinde genişler.
- `platform_yonetici` için 2FA/SSO S23 kapsamında ele alınacak (kurumsal güvenlik).
