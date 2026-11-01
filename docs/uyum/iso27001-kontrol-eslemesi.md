# ISO/IEC 27001:2022 Ek A — Kontrol Eşlemesi

Bu belge, ISO 27001 Ek A kontrollerinin **üründeki teknik karşılığını** işaretler. Bir
belgelendirme iddiası değildir: ISO 27001 bir **yönetim sistemi** standardıdır; politika,
risk değerlendirme, farkındalık eğitimi ve iç denetim gibi organizasyonel maddeler müşterinin
sorumluluğundadır. Buradaki amaç, denetim sorularına "ürün bunu nasıl karşılıyor" cevabını
tek yerden verebilmektir. Kalite yönetimi (ISO 9001) karşılığı: [iso9001-eslemesi.md](iso9001-eslemesi.md).

**Durum işaretleri:** ✅ üründe karşılanıyor · 🟡 kısmen · ⬜ ürün kapsamı dışında (organizasyonel)

Son gözden geçirme: 2026-11-01 (S28). Her satırın kanıtı kodda ya da testte durur; bir satır
✅'e ancak testi olan bir davranışla çıkar.

## A.5 — Organizasyonel kontroller

| Kontrol | Durum | Üründeki karşılığı |
|---|---|---|
| 5.15 Erişim denetimi | ✅ | RBAC izin sözlüğü (`kaynak:eylem`, 53 izin, 21 varsayılan rol), her uçta `require_perm`; görev ayrımı hem rolde (`satinalma:onay`, `ik:onay`, `stok:duzeltme`) hem kişide (kaydı açan onaylayamaz: satınalma, izin, fazla mesai, sayım) |
| 5.16 Kimlik yönetimi | ✅ | Tenant başına kullanıcı kaydı; SSO JIT provizyon + grup→rol senkronu |
| 5.17 Kimlik doğrulama bilgisi | ✅ | argon2id parola özeti, tenant parola politikası, TOTP 2FA (sır şifreli), kurtarma kodları (yalnız özet) |
| 5.18 Erişim hakları | ✅ | Rol/izin matrisi; platform panelinden entitlement; askıya alma erişimi anında keser |
| 5.23 Bulut hizmetleri güvenliği | 🟡 | Tenant izolasyonu (şema-başına-tenant), nesne deposu önek izolasyonu; sağlayıcı sözleşmeleri müşteride |
| 5.24–5.26 Olay yönetimi planı, değerlendirme, müdahale | ✅ | Önem dereceleri, roller, akış, iletişim şablonları: [olay-mudahale.md](../operasyon/olay-mudahale.md); nöbet ve yönlendirme: [nobet.md](../operasyon/nobet.md); SLO yanma hızı alarmları |
| 5.27 Olaylardan öğrenme | ✅ | Suçlamasız olay sonrası inceleme şablonu; her aksiyon test/alarm/runbook değişikliğine bağlanır |
| 5.28 Kanıt toplama | ✅ | Değiştirilemez denetim izi (DB trigger) + filtrelenebilir görüntüleyici + CSV dışa aktarma; güvenlik olayında kanıt koruma adımı |
| 5.29 Kesinti sırasında bilgi güvenliği | ✅ | Redis/MinIO/MQTT/DB kesintisinde zarif bozulma, testli (`test_s28_dayaniklilik.py`): yetki ve oran sınırı koruması kalkmaz, refresh güvenli tarafta 503 |
| 5.30 İş sürekliliği için BİT hazırlığı | ✅ | Tenant yedek/geri yükleme, PITR, tatbikat takvimi ve kayıtları ([dr.md](../operasyon/dr.md), [tatbikatlar/takvim.md](../operasyon/tatbikatlar/takvim.md)) |
| 5.33 Kayıtların korunması | ✅ | `denetim_izi` append-only; `consent_kayitlari` append-only |
| 5.34 Gizlilik ve KDK | ✅ | KVKK paketi: kişi bazlı ihraç, anonimleştirme, rıza defteri, TC maskeleme |

## A.8 — Teknolojik kontroller

| Kontrol | Durum | Üründeki karşılığı |
|---|---|---|
| 8.2 Ayrıcalıklı erişim hakları | ✅ | Ayrık control-plane kimliği (`platform_yonetici`, ayrı JWT tipi); platform yazmaları ayrı denetim izinde |
| 8.3 Bilgiye erişim kısıtlama | ✅ | Tenant çözümleme + `search_path` tek nokta; çapraz-tenant token reddi; dış portal firma kapsamı |
| 8.5 Güvenli kimlik doğrulama | ✅ | OAuth2 + rotasyonlu refresh (Redis iptal), TOTP 2FA, OIDC SSO (PKCE + nonce + state tek kullanım), giriş rate limit (Redis yoksa süreç içi yedek) |
| 8.6 Kapasite yönetimi | ✅ | NFR-01 k6 profili (`perf/k6/`), çok işçili API, gecikme SLO'su ve alarmı (ADR-0043) |
| 8.7 Kötü amaçlı yazılıma karşı koruma | ⬜ | Sunucu/uç nokta koruması altyapıda; ürün yüklenen belgeyi çalıştırmaz, yalnız saklar |
| 8.8 Teknik açıklıkların yönetimi | ✅ | CI'da pip-audit + npm audit (yüksek/kritik kapı), Dependabot (pip, npm, Actions, Docker), bandit; SBOM her build'de |
| 8.9 Yapılandırma yönetimi | 🟡 | Tenant güvenlik ayarları merkezî JSONB + platform paneli; prod'da zayıf `SECRET_KEY` ile açılış reddedilir; altyapı yapılandırması müşteride |
| 8.10 Bilgi silme | ✅ | KVKK anonimleştirme; ihraç artefaktları saklama süresi sonunda silinir (410) |
| 8.11 Veri maskeleme | ✅ | Staging kopyası anonimleştirilir (parola, TOTP, kişisel alanlar); yanıtlarda TC kimlik no ve sırlar maskeli |
| 8.12 Veri sızıntısı önleme | 🟡 | Yanıtlarda sır maskeleme (API anahtarı, webhook sırrı, OIDC client secret, TC kimlik no); gitleaks pre-commit; DLP ürün kapsamı dışında |
| 8.13 Bilgi yedekleme | ✅ | Tenant-farkında yedek + doğrulama + çeyreklik tatbikat; PITR (RPO = `archive_timeout`) |
| 8.15 Kayıt tutma (logging) | ✅ | Yapılandırılmış JSON log (`request_id` + `tenant`), denetim izi, platform denetim izi; Loki'de toplanır |
| 8.16 İzleme faaliyetleri | ✅ | Prometheus metrikleri, SLO yanma hızı alarmları, Sentry, OpenTelemetry izleri, Grafana panosu (ADR-0040) |
| 8.20 Ağ güvenliği | 🟡 | Tenant IP izin listesi (CIDR); ağ katmanı müşteri altyapısında |
| 8.24 Kriptografi kullanımı | ✅ | TLS (dağıtım), argon2id, HMAC-SHA256 webhook imzası, RS256 id_token doğrulaması, SHA-256 API anahtar özeti; özetlenemeyen sırlar (TOTP, webhook imza anahtarı) Fernet ile alan düzeyinde şifreli, anahtar döndürmeli (ADR-0047). **Açık:** OIDC client secret tenant ayar JSONB'sinde düz |
| 8.25 Güvenli geliştirme yaşam döngüsü | ✅ | ADR disiplini, CI kapıları (lint, tip, test, güvenlik taraması, mutasyon eşiği, sertleştirme taraması, SBOM) |
| 8.26 Uygulama güvenlik gereksinimleri | ✅ | Her uçta girdi doğrulama (Pydantic), istemci hatası ile sunucu hatası ayrımı: geçersiz değer/referans 422, çakışma 409; tarama 277 uçta 0 sunucu hatası |
| 8.28 Güvenli kodlama | ✅ | ruff + mypy strict + eslint + tsc strict, bandit, zorunlu tenant izolasyon/RBAC testleri, gitleaks |
| 8.29 Geliştirme ve kabulde güvenlik testi | ✅ | schemathesis taraması CI'da (`sertlestirme` işi), mutasyon testi eşiği %90, dayanıklılık senaryoları; WCAG taraması (axe, S27) sürüm öncesi elle |
| 8.30 Dış kaynaklı geliştirme | ⬜ | Organizasyonel |
| 8.31 Ortam ayrımı | ✅ | Anonim staging kopyası, tenant başına yalıtılmış göç, prod compose katmanı (ADR-0041) |
| 8.32 Değişiklik yönetimi | ✅ | ADR + yol haritası + CHANGELOG (sürüm notları komutla üretilir); göç fan-out up/down testli, göç öncesi tenant yedeği |
| 8.33 Test bilgisi | ✅ | Testler tek kullanımlık veritabanlarında, sentetik verilerle; staging gerçek veriyi yalnız anonim alır |
| 8.34 Denetim sırasında koruma | ✅ | Denetim okuma ayrı izinle (`denetim:oku`), `izleyici` rolüne otomatik verilmez |

## Bilinen boşluklar

| Boşluk | Durum |
|---|---|
| OIDC client secret düz metin (tenant güvenlik ayarları, public şema JSONB) | Açık — aynı `SifreliMetin` deseni JSONB alanına uygulanacak |
| Denetim kaydı saklama/imha otomasyonu | ADR-0022 ertelenmiş işler |
| Parola geçmişi/yaşı politikası | ADR-0022 ertelenmiş işler |
| Konteyner imajı imzalama (cosign) | Kayıt defteri ve yayın hattı kurulunca (ADR-0047 §İmaj imzalama); bugün imaj yalnız CI'da kurulup taranıyor |
| Dış erişilebilirlik yoklaması (blackbox) | İlk prod kurulumunda ([slo.md](../operasyon/slo.md)) |
