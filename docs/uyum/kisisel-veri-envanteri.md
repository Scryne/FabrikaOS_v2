# Kişisel Veri Envanteri (KVKK / VERBİS hazırlığı)

Bu belge FabrikaOS'un **ürün olarak** işlediği kişisel veri kategorilerini listeler.
Her müşteri (veri sorumlusu) kendi VERBİS kaydında bu envanteri kendi saklama süreleri ve
hukuki sebepleriyle somutlaştırır.

**Mimari not:** her tenant **ayrı PostgreSQL şemasında** yaşar (ADR-0003); kişisel veri
tenant'lar arasında paylaşılmaz. Dosya/artefaktlar nesne deposunda `tenant_<slug>/…`
önekiyle izole edilir.

## 1. Veri kategorileri

| Kategori | Tablo(lar) | Alanlar | Amaç | Hassas mı |
|---|---|---|---|---|
| Kimlik / hesap | `kullanici` | e-posta, ad soyad, parola özeti, son giriş | Kimlik doğrulama, yetkilendirme | Hayır |
| İkinci faktör | `kullanici`, `kurtarma_kodlari` | TOTP sırrı, kurtarma kodu özetleri | Hesap güvenliği | Hayır (kimlik doğrulayıcı) |
| Oturum / cihaz | `oturumlar` | IP adresi, user-agent, zaman damgaları | Güvenlik, adli iz | Hayır (trafik verisi) |
| Özlük | `personel` | **TC kimlik no**, ad, soyad, doğum tarihi, telefon, e-posta, departman, ünvan, işe giriş | İK süreçleri | **Evet** (TC kimlik no) |
| İzin / mesai | `izin_talepleri`, `fazla_mesailer` | tarih aralığı, gün sayısı, açıklama, onaylayan | İK süreçleri | Hayır |
| Zimmet / sertifika | `zimmetler`, `sertifikalar` | teslim edilen varlık, geçerlilik | İK / İSG | Hayır |
| İSG | `is_kazalari` | olay anlatımı, yaralanan personel, kayıp gün | Yasal İSG yükümlülüğü | **Evet** (sağlık verisi içerebilir) |
| Denetim izi | `denetim_izi` | kullanıcı e-postası, eylem, kaynak, IP, request id, detay | Hesap verebilirlik | Hayır |
| Rıza kayıtları | `consent_kayitlari` | rıza türü, metin sürümü, kabul/geri çekme, IP | İspat yükü | Hayır |
| Dış portal kullanıcıları | `kullanici.firma_id` | müşteri temsilcisi hesabı | Self-servis portal | Hayır |
| CRM kontak | `ortaklar` | ad, e-posta, telefon, ünvan | Ticari iletişim | Hayır |

## 2. Ürünün sağladığı KVKK yetenekleri

| Hak / yükümlülük | Karşılığı | Uç |
|---|---|---|
| **Erişim / taşınabilirlik** (m.11) | Kişi bazlı ihraç → ZIP (JSON) | `POST /kvkk/ihrac` → `GET /kvkk/ihraclar/{id}/indir` |
| **Silme / anonimleştirme** (m.7) | Zincirleme maskeleme, denetim izli, `onay="ANONIM"` şartı | `POST /kvkk/anonimlestir` |
| **Aydınlatma & açık rıza** (m.10) | Append-only rıza defteri; geri çekme yeni satır | `GET/POST /consent` |
| **Veri minimizasyonu** | TC kimlik no API yanıtlarında maskeli (son 2 hane), `ik:oku` izniyle sınırlı | `/personeller` |
| **Hesap verebilirlik** (m.12) | Değiştirilemez denetim izi (DB trigger) + görüntüleyici | `GET /denetim-kayitlari` |
| **Veri güvenliği** (m.12) | argon2id parola, TOTP 2FA, OIDC SSO, IP izin listesi, tenant izolasyonu | — |
| **Tenant bazlı toplu ihraç** | Platform admin tam şema dump'ı | `POST /platform/tenantlar/{id}/ihrac` |

**İhraç eksiksizliği:** ihraç, kişiye ait satırları **statik listeyle değil**,
`information_schema` üzerinden `%kullanici_id` / `%personel_id` desenli tüm kolonları
keşfederek toplar. Yeni modüller (ör. S25 sayım, S29 fatura) ek kod gerektirmeden kapsanır.

## 3. Bilinen sınırlar (ertelenmiş işler)

- **Saklama/imha politikası otomasyonu yok:** denetim izi ve rıza kayıtları süresiz birikir;
  periyodik imha müşterinin operasyonel sorumluluğundadır (ADR-0022 ertelenmiş işler).
- **TOTP sırrı** uygulama düzeyinde şifrelenmez (tenant-izole DB'de base32 durur).
- **Anonimleştirme** kimlik alanlarını maskeler; nesne deposundaki (DYS) belgelerin
  içeriğinde geçen kişisel veri **taranmaz**.
- `debug_claim_log` açıkken SSO claim'leri (e-posta, ad, grup) sunucu loguna yazılır —
  yalnız kurulum teşhisi için açılmalı, sonra kapatılmalıdır.
