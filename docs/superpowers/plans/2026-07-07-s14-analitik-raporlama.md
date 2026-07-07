# S14 Uygulama Planı — Analitik & Raporlama

TDD; görev-başına commit. Spec: `../specs/2026-07-07-s14-analitik-raporlama-design.md`.

1. **Bağımlılıklar + saf çekirdek.** `pyproject`: reportlab + openpyxl (+mypy override);
   `modules/rapor/birimler.py` (RAPOR_TURLERI/BICIMLERI/DURUMLARI) + `uretici.py`
   (`RaporIcerik` → `pdf_uret`/`xlsx_uret`). `test_s14_birim.py` + `test_s14_uretici.py`.
2. **Migration + model.** `modules/rapor/models.py` (Rapor); yeni tenant revision
   (down `f9b2d6e4a713`): `raporlar`; fan-out up/down testi (`test_s14_migration.py`).
3. **RBAC.** `izinler.py`: rol `analist`. `test_s14_seed.py`.
4. **Analitik modülü.** `modules/analitik/{schemas,repository,router}`:
   `/analitik/kpi` + `/analitik/trend`; `test_s14_analitik.py` (sayısal doğrulama +
   izolasyon + RBAC 403).
5. **Rapor servisi.** `modules/rapor/{repository,service}`: `rapor_olustur` +
   `uretim_planla`/`rapor_uret_calistir` (kendi oturumu, search_path, tür-bazlı veri
   çekiciler, to_thread üretim, NesneDepo yükleme, hazir/basarisiz + `rapor.hazir`).
   `test_s14_rapor_servis.py`.
6. **Rapor router + şemalar.** `POST /raporlar` 202, liste/detay/indir (409 hazir-değil);
   `api/router.py` include; `test_s14_rapor_api.py` (202→hazir→indir bayt eşleşmesi,
   izleyici 403, izolasyon 404); openapi regen.
7. **Docs.** ADR-0016; veri-sözlüğü (`raporlar`); yol-haritası + README S14 ✅.
8. **Frontend.** codegen; `modules/analitik` (hooks + AnalitikPano) + `modules/rapor`
   (sunum + hooks + RaporListesi/oluştur/indir); menü/rota (Zekâ); `modulKimlik`;
   i18n TR/EN; `olayIsle` `rapor.hazir`; vitest.
9. **Doğrulama.** BE ruff/format/mypy/pytest; FE eslint/tsc/prettier/vitest/build;
   canlı e2e: taze tenant + gerçek MinIO → rapor 202→hazir→indir + KPI doğru +
   tarayıcı teyidi.
