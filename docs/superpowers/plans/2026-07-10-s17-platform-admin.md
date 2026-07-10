# S17 — Platform Admin Paneli (Görev Planı)

Spec: `docs/superpowers/specs/2026-07-10-s17-platform-admin-design.md` · Dal:
`feat/s17-platform-admin` (S16 dalı üstünde) · TDD, görev-başına commit.

- [x] **T1 — Dokümanlar:** spec + bu plan; commit.
- [x] **T2 — Migration + modeller:** public revision (platform_yonetici,
  tenant_ihraclari, platform_denetim_izi) + `control_plane/models.py` +
  `test_s17_migration.py` (head'de var, down'da yok, up geri gelir).
- [x] **T3 — Platform kimlik:** `jwt.platform_access_uret/platform_refresh_uret`;
  `app/platform/deps.py` (`mevcut_platform_yonetici`); `app/platform/kimlik_router.py`
  (`token/yenile/cikis/ben`, rate-limit); `scripts/platform_yonetici_olustur.py`;
  `test_s17_platform_kimlik.py` (giriş, 401'ler, düzlem ayrımı, rotasyon).
- [x] **T4 — Okuma uçları:** `app/platform/{service,schemas,router}.py` — tenantlar
  liste/detay, abonelikler, planlar, saglik; `test_s17_platform_okuma.py`.
- [x] **T5 — Yaşam döngüsü:** provizyon POST (db_url enjeksiyonlu), PATCH,
  askıya-al/aktifleştir, DELETE (onay=slug + DROP SCHEMA CASCADE); platform audit
  yardımcıi; `test_s17_tenant_yasam.py` (askıya→404 ANINDA, provizyon→giriş,
  sil→şema yok + onay uyuşmazlığı 422).
- [x] **T6 — Entitlement yazma:** PUT modul-haklari/ozellik-bayraklari;
  `test_s17_entitlement_yaz.py` (tenant'ta anında 403/200, katalog dışı 422, audit).
- [x] **T7 — KVKK ihracı:** `app/platform/ihrac.py` (görev + ZIP üretimi) + uçlar;
  `test_s17_ihrac.py` (es-zamanlı görev: durum akışı, zip içeriği, indir 409/200).
- [x] **T8 — Codegen:** openapi.json regen + `npm run codegen`.
- [x] **T9 — FE altyapı:** `src/platform/` store + istemci + giriş + kabuk
  (turuncu hat + PLATFORM filigranı) + rotalar + i18n; vitest.
- [x] **T10 — FE ekranlar:** TenantListesi, TenantDetay (entitlement switch +
  tehlikeli aksiyonlar slug-onay modalı), ProvizyonSihirbazi, SaglikPano,
  AbonelikListesi; vitest.
- [x] **T11 — Dokümantasyon + DoD:** ADR-0019, veri-sozlugu, yol-haritasi S17 ✅,
  README; BE pytest+ruff+mypy / FE vitest+eslint+tsc+build tam koşu.
- [x] **T12 — Canlı doğrulama:** dev DB'ye karşı uvicorn + tarayıcı (provizyon
  sihirbazı → yeni tenant'a giriş; askıya alma; ihraç indir; entitlement switch).
