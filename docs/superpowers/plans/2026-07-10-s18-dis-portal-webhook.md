# S18 — Dış Portal + Webhook + API Entegrasyon (Görev Planı)

Spec: `docs/superpowers/specs/2026-07-10-s18-dis-portal-webhook-design.md` · Dal:
`feat/s18-dis-portal-webhook` (S17 dalı üstünde) · TDD, görev-başına commit.

- [x] **T1 — Dokümanlar:** spec + bu plan; dal; commit.
- [x] **T2 — Migration + modeller:** tenant revision (webhook_abonelikleri,
  webhook_teslimatlari, api_anahtarlari, kullanici.firma_id) +
  `modules/entegrasyon/models.py` + `test_s18_migration.py`.
- [x] **T3 — Katalog/izin/rol:** `entegrasyon` + `dis-portal` modülleri; izinler
  `entegrasyon:oku/yaz` + `dis:erisim`; roller `entegrasyon` + `dis-panel`;
  `webhook_erisimi_gerekli` (modül VEYA `webhook-onizleme` bayrağı — S16 tüketimi);
  `test_s18_entitlement.py` (temel 403 MODUL_KAPALI, bayrak açar, provizyon idempotent).
- [x] **T4 — İmza çekirdeği:** `entegrasyon/imza.py` (imza_uret/imza_dogrula/
  zarf_olustur/sonraki_deneme — saf) + `test_s18_imza.py`.
- [x] **T5 — Webhook yönetim uçları:** CRUD + anahtar-yenile + olay-turleri +
  teslimat günlüğü + yeniden-dene; `test_s18_webhook_ucler.py` (RBAC, maskeleme,
  bir-kez anahtar, katalog dışı 422, izolasyon).
- [x] **T6 — Relay:** `entegrasyon/relay.py` (fan-out + teslimat + backoff) +
  `scripts/webhook_relay.py` (--tek-tur/--araligi/--tenant);
  `test_s18_relay.py` (MockTransport: imza doğrulama, retry, terminal, izolasyon).
- [x] **T7 — API anahtarı:** model uçları (bir-kez göster, SHA-256 özet) +
  `api_izin_gerekli` + `/entegrasyon/{stok-bakiyeleri,satinalma-talepleri,
  uretim-ozeti}`; `test_s18_api_anahtar.py`.
- [x] **T8 — Yeni olaylar:** `ariza.olustu` (arıza POST outbox) + `oee.dustu`
  (`POST /oee/dusuk-tara`, makine+gün dedup); `test_s18_olaylar.py`.
- [x] **T9 — Dış portal backend:** `dis_firma_gerekli` + `/dis/talepler` (GET/POST/
  {id}) + `/dis/durum` + kullanıcı DTO `firma_id`; `test_s18_dis_portal.py`
  (firma A/B izolasyonu, firmasız 403, iç uca 403).
- [x] **T10 — Codegen:** openapi.json regen + `npm run codegen`.
- [x] **T11 — FE /webhooklar:** üç sekme (Abonelikler / Teslimat Günlüğü / API
  Anahtarları) + bir-kez anahtar modalı + payload çekmecesi + yeniden dene + menü
  + i18n; vitest.
- [x] **T12 — FE dış portal:** `/dis` hafif kabuk (Taleplerim · Yeni Talep) + durum
  zaman çizelgesi (müşteri-dili) + giriş yönlendirmesi + i18n; vitest.
- [x] **T13 — Dokümantasyon + DoD:** ADR-0020, veri-sozlugu, yol-haritasi S18 ✅,
  README; BE pytest+ruff+mypy / FE vitest+eslint+tsc+build tam koşu.
- [x] **T14 — Canlı doğrulama:** dev DB + uvicorn + relay `--tek-tur`: abonelik →
  olay → yerel alıcıda imza doğrulama → retry; API anahtarıyla `/entegrasyon`
  çekme; dış portal + webhook ekranı tarayıcı turu (Playwright MCP).
