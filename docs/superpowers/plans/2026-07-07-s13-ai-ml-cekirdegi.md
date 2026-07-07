# S13 Uygulama Planı — AI/ML Çekirdeği

TDD; görev-başına commit. Spec: `../specs/2026-07-07-s13-ai-ml-cekirdegi-design.md`.

1. **Bağımlılıklar + saf çekirdek.** `pyproject`: pandas + scikit-learn (+joblib) + mypy
   overrides; `modules/ai/birimler.py` (MODEL_TURLERI, MODEL_DURUMLARI, risk_seviyesi).
   `test_s13_birim.py`.
2. **Feature pipeline.** `ozellikler.py`: `gunluk_makine_ozeti`, `bakim_ozellikleri`
   (+`bakim_guncel_ozellikler`), `oee_gecikme_ozellikleri` (+son pencere),
   `stok_tuketim_gunluk`. Sentetik verili birim testler.
3. **Model katmanı.** `modeller.py`: 4 egit/tahmin çifti + `EgitimSonucu` + `YetersizVeri`
   + tur→fonksiyon registry; deterministik; çıktı doğrulama testleri.
4. **Migration.** Yeni tenant revision (down `e1f4a2c3b567`): `model_kayitlari` +
   `tahminler`; fan-out up/down testi (`test_s13_migration.py`).
5. **Modeller + artefakt.** `models.py` (ModelKaydi, Tahmin); `artefakt.py` (joblib ↔
   `NesneDepo`, tenant-önekli anahtar, süreç-içi önbellek). `test_s13_artefakt.py`.
6. **RBAC.** `izinler.py`: `ai:egit` + rol `ai`. `test_s13_seed.py`.
7. **Eğitim servisi.** `repository.py` (kayıt CRUD + DataFrame veri çekiciler);
   `service.egitim_baslat/egitim_calistir` (kendi oturumu, search_path, to_thread,
   aktif rotasyonu, basarisiz yolu, `ai.model` realtime). `test_s13_egitim.py`.
8. **Çıkarım servisi.** `service.tahmin_calistir` (aktif model + önbellek, geçmiş satırı,
   anomalide `anomali.tespit` outbox + realtime). `test_s13_tahmin.py`.
9. **Router + şemalar.** `/tahmin/*` uçları (Zarf, audit, 202/404/403); `api/router.py`
   include; izolasyon + RBAC testleri; openapi regen.
10. **Docs.** ADR-0015; veri-sözlüğü (`model_kayitlari`, `tahminler`); yol-haritası +
    README S13 ✅.
11. **Frontend.** codegen; `modules/ai` (hooks + TahminPanosu); `modulKimlik` "zeka"
    hattı; menü/rota; i18n TR/EN; `olayIsle` (`ai.model`, `anomali.tespit`); vitest.
12. **Doğrulama.** BE ruff/format/mypy/pytest; FE eslint/tsc/prettier/vitest/build;
    canlı e2e: taze tenant + gerçek MinIO → eğit → `hazir` → 4 tahmin ucu + anomali
    outbox + tarayıcı teyidi.
