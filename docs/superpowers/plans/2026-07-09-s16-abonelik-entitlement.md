# S16 — Abonelik, Entitlement & Feature Flag (Uygulama Planı)

Spec: `../specs/2026-07-09-s16-abonelik-entitlement-design.md` · Dal:
`feat/s16-abonelik-entitlement` · TDD, görev başına commit.

## Görevler

1. **T1 Saf çekirdek** — `control_plane/moduller.py` (MODUL_KATALOGU 17,
   OZELLIK_KATALOGU, PLAN_KATALOGU 4) + `control_plane/entitlement.py`
   (modul_acik_mi / etkin_moduller / ozellik_acik_mi / etkin_ozellikler; fail-closed).
   Test: `tests/test_s16_birim.py`.
2. **T2 Modeller + public migration** — `Plan`/`ModulHakki`/`OzellikBayragi`
   (public); migration #2: 3 tablo + plan seed (statik) + `abonelik.plan_kodu` FK.
   Test: `tests/test_s16_migration.py` (public up/down roundtrip).
3. **T3 Enforcement** — `control_plane/entitlement_service.py` +
   `core/deps.modul_gerekli` + 19 router'a bağlama. Testler: 403 MODUL_KAPALI,
   admin bypass edemez, override anında etkili, tenant izolasyonu.
4. **T4 Koltuk limiti** — `POST /kullanicilar`'da FOR UPDATE + sayım; 409
   KOLTUK_LIMITI. Testler: limit doldu → 409, pasif sayılmaz.
5. **T5 Uçlar** — `app/modules/abonelik/` `GET /moduller` (oturum) + `GET /abonelik`
   (`abonelik:oku`); izin kataloğu güncelle. Testler: içerik + RBAC 403.
6. **T6 Provizyon + script** — `_plan_tohumla` upsert; geçersiz plan_kodu ValueError;
   `scripts/entitlement_ayarla.py` CLI. Test: idempotent + red.
7. **T7 Docs** — ADR-0018, veri-sozlugu, yol-haritasi S16 ✅, README, openapi regen.
8. **T8 FE altyapı** — codegen; `modules/abonelik/hooks.ts`; `menu.ts` modul alanı +
   süzgeç; `routes/ModulKapisi.tsx`; App.tsx rota sarma. Testler.
9. **T9 FE ekran** — `/abonelik` AbonelikSayfasi + menü + i18n TR/EN. Test.
10. **T10 Tam doğrulama** — BE pytest/ruff/mypy + FE vitest/eslint/prettier/tsc/build.
11. **T11 Canlı e2e** — s16live (temel plan) + uvicorn :8016 + HTTP e2e + gerçek
    tarayıcı (menü süzgeci, upsell, /abonelik ekranı).
