# Kurumsal SSO (OIDC) Kurulum Kılavuzu

> **Durum:** Akış sahte IdP ile uçtan uca testlidir; **canlı Azure AD / Google Workspace
> doğrulaması henüz yapılmamıştır** (ADR-0022). Bu belge, ilk canlı denemede doldurulacak
> alanları ve teşhis yolunu tarif eder.

Yapılandırma **tenant başınadır** ve platform panelinden girilir:
`/platform` → ilgili tenant → **Güvenlik ayarları** → *Kurumsal SSO (OIDC)*.

## 1. Doldurulacak alanlar

| Panel alanı | Karşılığı | Nereden alınır |
|---|---|---|
| **Issuer** | `issuer` | Sağlayıcının `/.well-known/openid-configuration` adresinin **kök** kısmı (sonundaki `/.well-known/...` yazılmaz) |
| **İstemci kimliği** | `client_id` | IdP'de oluşturulan uygulama kaydı |
| **İstemci sırrı** | `client_secret` | IdP uygulama kaydı → sertifikalar & sırlar |
| **Dönüş adresi** | `redirect_uri` | **Bu üründe sabittir:** `https://<tenant-alan-adi>/sso/donus` |
| İzinli e-posta alan adları | — | Opsiyonel; boşsa kısıt yok |
| Varsayılan roller | — | JIT ile açılan hesaba verilecek roller (ör. `izleyici`) |
| E-posta / grup claim'i | `claim_eslemesi` | Sağlayıcıya göre değişir (aşağıda) |

`redirect_uri` **istemciden alınmaz**; IdP kaydındaki değerle panelde girilen değer
**birebir** aynı olmalıdır (aksi hâlde IdP `redirect_uri_mismatch` döner).

## 2. Sağlayıcıya özel değerler

### Microsoft Entra ID (Azure AD)

- **Issuer:** `https://login.microsoftonline.com/<directory-tenant-id>/v2.0`
- Uygulama kaydı → *Authentication* → Platform: **Web** → Redirect URI: `https://<alan>/sso/donus`
- *Certificates & secrets* → **New client secret**
- **E-posta claim'i:** genelde `email`; kiracıda e-posta yayınlanmıyorsa
  **`preferred_username`** ya da `upn` denenir.
- **Grup claim'i:** varsayılan olarak **gelmez**. *Token configuration* → *Add groups claim*
  ile açılır; grup **ID**'leri (GUID) gelir, ad değil → `grup_rol_eslemesi` anahtarları GUID olur.
  Ad ile eşleme isteniyorsa Entra'da grup adlarının yayınlanması ayrıca yapılandırılmalıdır.

### Google Workspace

- **Issuer:** `https://accounts.google.com`
- Google Cloud Console → *APIs & Services* → *Credentials* → **OAuth client ID** (Web application)
- Authorized redirect URI: `https://<alan>/sso/donus`
- **E-posta claim'i:** `email`
- **Grup claim'i:** ID token'da **yoktur**. Grup bazlı rol eşlemesi Google'da bu sürümde
  desteklenmez → `varsayilan_roller` kullanılır, roller uygulamadan yönetilir.

### Keycloak (şirket içi)

- **Issuer:** `https://<host>/realms/<realm>`
- **Grup claim'i:** `groups` (client scope ile eklenir) ya da `realm_access.roles`
  (iç içe yol nokta ile yazılır).

## 3. İlk canlı deneme — teşhis

Claim adları beklenenden farklıysa **kod değişikliği gerekmez**:

1. Panelde **Claim ayıklama logu**'nu (`debug_claim_log`) açın.
2. Bir kez SSO ile giriş deneyin.
3. Sunucu logunda `app.oidc` logger'ı `WARNING` seviyesinde **ham ID token claim'lerini**
   yazar (JSON formatlı log satırı).
4. Gördüğünüz claim adlarını panelde *E-posta claim'i* / *Grup claim'i* alanlarına yazın.
5. **Teşhis bitince `debug_claim_log`'u kapatın** — açık kalırsa kişisel veri (e-posta, ad,
   grup üyelikleri) log dosyalarına yazılmaya devam eder.

## 4. Sık karşılaşılan hatalar

| Belirti | Sebep |
|---|---|
| `redirect_uri_mismatch` | IdP kaydındaki adres ile paneldeki `donus_url` birebir aynı değil |
| 401 "ID token doğrulanamadı: Audience doesn't match" | Panel `istemci_id` ile IdP uygulaması farklı |
| 401 "nonce eşleşmedi" | Akış yeniden başlatılmadan eski bağlantı kullanıldı (state tek kullanımlık) |
| 403 `SSO_ALAN_ADI` | Kullanıcının e-posta alan adı *İzinli alan adları* listesinde yok |
| 403 `SSO_KULLANICI_YOK` | JIT kapalı ve kullanıcı sistemde tanımlı değil |
| 409 `KOLTUK_LIMITI` | JIT yeni kullanıcı açacak ama plan koltuk limiti dolu |
| 404 (SSO düğmesi yok) | Yapılandırma yarım: issuer / client_id / secret / redirect_uri'den biri boş |

## 5. Güvenlik notları

- İstemci sırrı panelde **maskeli** gösterilir; alanı boş bırakmak ya da maskeyi olduğu gibi
  bırakmak **mevcut sırrı korur**. Sırrı değiştirmek için yeni değeri yazın.
- SSO ile açılan hesaplar parola akışıyla giremez (kullanılamaz parola özeti yazılır).
- Kullanıcı kendi TOTP 2FA'sını açtıysa SSO'dan sonra da ikinci adım istenir.
- Tenant'ın "2FA zorunlu" ayarı SSO girişinde karşılanmış sayılır (ikinci faktör IdP'dedir).
