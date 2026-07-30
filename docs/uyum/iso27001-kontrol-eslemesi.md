# ISO/IEC 27001:2022 Ek A — Kontrol Eşlemesi (başlangıç)

Bu belge, ISO 27001 Ek A kontrollerinin **üründeki teknik karşılığını** işaretler. Bir
belgelendirme iddiası değildir: ISO 27001 bir **yönetim sistemi** standardıdır; politika,
risk değerlendirme, farkındalık eğitimi ve iç denetim gibi organizasyonel maddeler müşterinin
sorumluluğundadır. Buradaki amaç, denetim sorularına "ürün bunu nasıl karşılıyor" cevabını
tek yerden verebilmektir.

**Durum işaretleri:** ✅ üründe karşılanıyor · 🟡 kısmen · ⬜ ürün kapsamı dışında (organizasyonel)

## A.5 — Organizasyonel kontroller

| Kontrol | Durum | Üründeki karşılığı |
|---|---|---|
| 5.15 Erişim denetimi | ✅ | RBAC izin sözlüğü (`kaynak:eylem`), her uçta `require_perm`; görev ayrımı (`satinalma:onay`, `ik:onay`, `stok:duzeltme`) |
| 5.16 Kimlik yönetimi | ✅ | Tenant başına kullanıcı kaydı; SSO JIT provizyon + grup→rol senkronu |
| 5.17 Kimlik doğrulama bilgisi | ✅ | argon2id parola özeti, tenant parola politikası, TOTP 2FA, kurtarma kodları (yalnız özet) |
| 5.18 Erişim hakları | ✅ | Rol/izin matrisi; platform panelinden entitlement; askıya alma erişimi anında keser |
| 5.23 Bulut hizmetleri güvenliği | 🟡 | Tenant izolasyonu (şema-başına-tenant), nesne deposu önek izolasyonu; sağlayıcı sözleşmeleri müşteride |
| 5.28 Kanıt toplama | ✅ | Değiştirilemez denetim izi (DB trigger) + filtrelenebilir görüntüleyici |
| 5.33 Kayıtların korunması | ✅ | `denetim_izi` append-only; `consent_kayitlari` append-only |
| 5.34 Gizlilik ve KDK | ✅ | KVKK paketi: kişi bazlı ihraç, anonimleştirme, rıza defteri, TC maskeleme |

## A.8 — Teknolojik kontroller

| Kontrol | Durum | Üründeki karşılığı |
|---|---|---|
| 8.2 Ayrıcalıklı erişim hakları | ✅ | Ayrık control-plane kimliği (`platform_yonetici`, ayrı JWT tipi); platform yazmaları ayrı denetim izinde |
| 8.3 Bilgiye erişim kısıtlama | ✅ | Tenant çözümleme + `search_path` tek nokta; çapraz-tenant token reddi; dış portal firma kapsamı |
| 8.5 Güvenli kimlik doğrulama | ✅ | OAuth2 + rotasyonlu refresh (Redis iptal), TOTP 2FA, OIDC SSO (PKCE + nonce + state tek kullanım), giriş rate limit |
| 8.9 Yapılandırma yönetimi | 🟡 | Tenant güvenlik ayarları merkezî JSONB + platform paneli; altyapı yapılandırması müşteride |
| 8.12 Veri sızıntısı önleme | 🟡 | Yanıtlarda sır maskeleme (API anahtarı, webhook sırrı, OIDC client secret, TC kimlik no); DLP ürün kapsamı dışında |
| 8.15 Kayıt tutma (logging) | ✅ | Yapılandırılmış JSON log (`request_id` + `tenant`), denetim izi, platform denetim izi |
| 8.16 İzleme faaliyetleri | ⬜ | S19 (gözlemlenebilirlik) kapsamında — Sentry/Prometheus/OTel henüz yok |
| 8.20 Ağ güvenliği | 🟡 | Tenant IP izin listesi (CIDR); ağ katmanı müşteri altyapısında |
| 8.24 Kriptografi kullanımı | 🟡 | TLS (dağıtım), argon2id, HMAC-SHA256 webhook imzası, RS256 id_token doğrulaması, SHA-256 API anahtar özeti. **Eksik:** TOTP sırrı uygulama düzeyinde şifrelenmiyor |
| 8.28 Güvenli kodlama | 🟡 | ruff + mypy strict + eslint + tsc strict, zorunlu tenant izolasyon/RBAC testleri. **Eksik:** SAST/SBOM (S28) |
| 8.31 Ortam ayrımı | ⬜ | Staging ayrımı S20 kapsamında |
| 8.32 Değişiklik yönetimi | 🟡 | Conventional Commits + ADR disiplini + migration fan-out (up/down). CI kapıları S28'de derinleşir |
| 8.34 Denetim sırasında koruma | ✅ | Denetim okuma ayrı izinle (`denetim:oku`), `izleyici` rolüne otomatik verilmez |

## Bilinen boşluklar (yol haritasıyla eşleşen)

| Boşluk | Nerede kapanacak |
|---|---|
| Merkezî izleme, alerting, SLO | S19 — Gözlemlenebilirlik |
| Yedekleme/DR, geri yükleme tatbikatı, ortam ayrımı | S20 — Yedekleme/DR + Staging |
| SBOM, bağımlılık tarama, imza, mutation testing | S28 — Kurumsal Güvence |
| Denetim kaydı saklama/imha otomasyonu | ADR-0022 ertelenmiş işler |
| TOTP sırrı şifrelemesi, parola geçmişi/yaşı | ADR-0022 ertelenmiş işler |
