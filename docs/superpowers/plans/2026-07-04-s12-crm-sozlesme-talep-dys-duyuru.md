# S12 Uygulama Planı — CRM/Sözleşme/Talep + DYS + Duyuru + Ticari Pano

TDD; görev-başına commit. Spec: `../specs/2026-07-04-s12-...-design.md`.

1. **RBAC katalog + roller.** `izinler.py`: `crm:yaz`, `sozlesme:oku/yaz`, `talep:oku`,
   `duyuru:oku/yaz`; roller `crm`, `dokuman`, `duyuru`. Seed testi (`test_s12_seed.py`).
2. **Migration** `e1f4a2c3b567` (down `d5c8e1f0a927`): 7 tablo, FK sırası
   (firmalar→ortaklar, sozlesmeler, talepler, belgeler→belge_surumleri, duyurular).
   Fan-out up/down testi (`test_s12_migration.py`).
3. **Saf çekirdek + modeller.** `crm/sozlesme/talep/dys/duyuru` `models.py`; `birimler.py`
   (beyaz-listeler); `sozlesme/durum.py`, `talep/durum.py`; `sozlesme` yaklasan saf fn.
   Birim testleri (`test_s12_birim.py`).
4. **CRM uçları.** firma CRUD + ortak (firma_id filtreli). `test_s12_crm.py`
   (CRUD, izolasyon, RBAC, ortak-firma bağı).
5. **Sözleşme uçları.** CRUD + durum geçiş + `/yaklasan` + `/yaklasanlari-tara`
   (kenar-tetikli outbox). `test_s12_sozlesme.py` (oto kod, durum 409, yaklasan tara bir-kez,
   izolasyon, RBAC).
6. **Talep uçları.** CRUD + durum geçiş + atama. `test_s12_talep.py`.
7. **DYS.** `depolama.py` (`NesneDepo` protokol + `MinioNesneDepo` + `BellekNesneDepo` +
   `nesne_depo_al`/`nesne_depo_ayarla`); belge CRUD + sürüm upload (multipart)/download.
   `test_s12_dys.py` (sürümleme, indirme içerik eşleşmesi, tenant-önek izolasyonu, RBAC).
8. **Duyuru.** CRUD + yayinla/kaldir + `duyuru.yeni` realtime. `test_s12_duyuru.py`.
9. **Ticari özet.** `GET /ticari/ozet` (crm:oku). `test_s12_ticari.py`.
10. **Config/router/env.** `config.py` MinIO ayarları; `pyproject` `minio` dep; `.env.example`
    (var); `api/router.py` include; `main` startup depo init (best-effort bucket ensure).
11. **Docs.** ADR-0014; openapi regen; veri-sözlüğü (ortak/belge_surumu) + yol-haritası +
    README S12 ✅.
12. **Frontend.** codegen; hooks + ekranlar (crm/sozlesme/talep/dys/duyuru) + durum aynaları
    + rozetler; menü bölümleri (Ticari, Doküman/Duyuru); rotalar; i18n TR/EN; `olayIsle`;
    `TicariPano`; vitest.
13. **Doğrulama.** BE ruff/format/mypy/pytest; FE eslint/tsc/prettier/build/vitest; taze
    tenant migrate; HTTP e2e + gerçek tarayıcı + MinIO round-trip.
