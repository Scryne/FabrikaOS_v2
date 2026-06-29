# ADR-0005: Kimlik & Yetkilendirme — OAuth2/JWT + argon2id + RBAC

Durum: Kabul
Tarih: 2026-06-29

## Bağlam
Tenant kullanıcıları güvenli kimlik doğrulamasına ve modül bazında ince yetkilendirmeye
ihtiyaç duyar. Kullanıcılar ve roller tenant'a özeldir (her tenant kendi şemasında).
Token hırsızlığı/yeniden kullanımı ve brute-force riski azaltılmalıdır.

## Karar
- **OAuth2 şifre akışı + JWT (HS256).** Kısa ömürlü **access** (15 dk) + **refresh** (7 gün).
- **Refresh rotasyonu + Redis iptal listesi:** her yenilemede eski `jti` iptal edilir, yeni
  çift üretilir; çıkışta refresh iptal edilir. Tekrar kullanılan/iptalli refresh → 401.
- **Parola: argon2id** (`argon2-cffi`); `check_needs_rehash` ile parametre güncellemesine hazır.
- **RBAC:** ilişkisel `rol / izin / rol_izin / kullanici_rol`. İzin biçimi `modul:islem`
  (`uretim:yaz`, `kullanici:oku`, `satinalma:onay`, ...). Her korumalı uçta
  `Depends(izin_gerekli("modul:islem"))`. En az ayrıcalık ilkesi.
- **İki dependency altın kuralı:** tenant-kapsamlı uç `tenant_cozumle` (izolasyon) + `izin_gerekli`
  (RBAC) zincirinden geçer. `tenant_cozumle`, `mevcut_kullanici` ve uç gövdesi aynı istek
  oturumunu (ve `search_path`'i) paylaşır.
- **Cross-tenant koruması:** JWT `tenant_slug` ≠ istek tenant'ı → 403. Yetkisiz izin → 403;
  başka tenant'a ait kaynak → 404 (görünmez).
- **Audit:** yazma işlemleri `denetim_izi`'ne kim-ne-ne zaman (+`request_id`) kaydeder.
- **Rate limit:** `/kimlik/token` Redis sabit-pencere ile sınırlanır (brute-force azaltma).

## Sonuçlar
- (+) Kısa access + rotasyonlu refresh, çalınmış token penceresini daraltır.
- (+) RBAC modül-bazlı satışa (entitlement, S16) ve menü gizlemeye temel olur.
- (+) İzolasyon + RBAC + audit zorunlu testlerle güvencelenir (Faz 0 geçiş kapısı).
- (−) HS256 simetrik anahtar tek `SECRET_KEY`'e bağlı; üretimde rotasyon/asimetrik (RS256) ve
  2FA ileride değerlendirilecek.
- (−) JWT durumsuz olduğundan access iptali yoktur; bu yüzden access ömrü kısa tutulur.
