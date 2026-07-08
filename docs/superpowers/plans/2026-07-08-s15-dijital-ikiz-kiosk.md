# S15 Uygulama Planı — Dijital İkiz + Kiosk

Spec: `docs/superpowers/specs/2026-07-08-s15-dijital-ikiz-kiosk-design.md`.
Dal: `feat/s15-dijital-ikiz-kiosk`. TDD, görev-başına commit.

## Görevler

1. **Model + migration** — `modules/ikiz/models.py` (`IkizDugum`); tenant migration
   `ikiz_dugumleri` (down `b4e8f2a6c159`), up/down fan-out testli.
2. **Yerleşim uçları** — `schemas/repository/router`: `GET/PUT /ikiz/yerlesim`
   (PUT replace-all + doğrulama 422 + audit + `ikiz.yerlesim` yayını). Testler:
   roundtrip, mükerrer/yok-makine 422, x/y sınır 422, RBAC 403, tenant izolasyonu.
3. **Durum ucu** — `GET /ikiz/durum?saat=` (ozet + dugumler + yerlesmemis;
   `donem_oee` yeniden kullanımı). Testler: sentetik veriyle sayısal doğruluk,
   pencere filtresi, izolasyon.
4. **Kiosk rolü** — `VARSAYILAN_ROLLER["kiosk"]` = {uretim:oku}; kiosk rolü yazma
   uçlarında 403 + durum ucunda 200 testi.
5. **Docs + codegen** — ADR-0017, veri sözlüğü, yol haritası/README S15 ✅;
   `frontend/openapi.json` regen + `npm run codegen`.
6. **FE ikiz** — `modules/ikiz/{sunum.ts(+test),hooks.ts,IkizSayfasi.tsx}` + rota
   `/ikiz` + menü (Üretim) + i18n TR/EN + `olayIsle` invalidate (+test).
7. **FE kiosk** — `modules/kiosk/KioskSayfasi.tsx(+test)` + kabuksuz rota `/kiosk`
   + i18n; ikiz sayfasından "Kiosk modu" girişi.
8. **Doğrulama** — BE pytest+ruff+mypy; FE vitest+eslint+tsc+build; taze `s15live`
   tenant canlı HTTP e2e + gerçek tarayıcı (ikiz canlı durum + kiosk) ekran görüntüleri.
