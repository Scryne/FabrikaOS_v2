# ADR-0008: Frontend SPA mimarisi + auth (S5)

Durum: Kabul
Tarih: 2026-06-29

## Bağlam
Faz 1'in ilk frontend sprint'i: çok-kiracılı MES+ERP için gösterilebilir bir SPA iskeleti +
kimlik akışı. Backend tenant'ı subdomain veya `X-Tenant` başlığından çözer ve JWT
(kısa access + rotasyonlu refresh, JSON döner) kullanır. Ürün "eşsiz" ve profesyonel
olmalı; ama veri-yoğun ERP ekranları (S6) için hızlı geliştirme de gerekir.

## Karar
- **Yığın:** Vite + React 18 + TypeScript (strict) + **Ant Design v5**, React Router 6,
  TanStack Query, Zustand, i18next. Paket yöneticisi npm.
- **Stil — hibrit "AntD motoru + özel deri":** Karmaşık veri bileşenleri (Table/Form/
  DatePicker) AntD'den; görünüm tamamen özel — `ConfigProvider` koyu tema token'ları
  (`tema.ts`) + CSS değişkenleri (`index.css`). Düz AntD "templated" görünmez; eşsizlik
  derin temadan ve özel app shell'den gelir. (Bkz. PRODUCT.md / DESIGN.md.)
- **Görsel yön:** endüstriyel kontrol odası, **yalnız koyu**; amber birincil + cyan info
  sinyal vurgusu, sayısal değerlerde monospace, yüksek kontrast. Strateji: Restrained.
- **Tenant çözümleme (istemci tarafı):** Frontend ile API ayrı origin olduğundan tenant
  client'ta çözülür: önce subdomain (`alfa.localhost` / `alfa.fabrikaos.com`), yoksa
  login'deki "Firma kodu" (fallback) → `localStorage` → her isteğe `X-Tenant` başlığı.
- **API katmanı:** `openapi-typescript` ile backend OpenAPI'den **tipler** üretilir
  (commit edilir; build backend'siz çalışır). Özel, tiplenmiş `apiClient` tek noktada
  **interceptor**'dur: `X-Tenant` + `Bearer` enjekte; **401 → `/kimlik/yenile` → orijinali
  tek tekrar**, eşzamanlı 401'ler için **single-flight** yenileme; refresh de düşerse oturum
  düşürülür. TanStack Query hook'ları elle (S6'da modül hook'ları).
- **Token saklama:** access **bellekte** (Zustand, kalıcı değil; XSS kalıcı sızıntısını
  azaltır), refresh **localStorage**'da; sayfa yükünde `oturumBaslat` ile sessiz giriş.
  Backend'in refresh rotasyonu + Redis iptali riski sınırlar. (httpOnly cookie sertleştirme
  ileride — backend değişikliği gerektirir.)
- **RBAC + rotalar:** `KorunanRota` (oturum kapısı) + `IzinKapisi` (izin kapısı, 403);
  kenar çubuğu menüsü `gorunurMenu` ile RBAC'a göre **filtrelenir** (yetki yoksa öğe gizli).
- **i18n:** TR varsayılan, EN opsiyonel; tüm metin `t(...)` (hardcode yok).
- **Test:** Vitest + React Testing Library + MSW/fetch-mock. 32 test: tenant çözümleme,
  authStore, interceptor (401/refresh/retry/logout), kimlik servisi, RBAC menü, korunan
  rota, giriş ekranı. `tsc --strict`, ESLint, Prettier temiz; `vite build` geçer.

## Sonuçlar
- (+) Demo'ya hazır, eşsiz ve erişilebilir bir kabuk + güvenli auth akışı; S6 veri ekranları
  için sağlam zemin (AntD veri bileşenleri + tiplenmiş API katmanı hazır).
- (+) Tip güvenliği uçtan uca: OpenAPI → TS tipleri; sözleşme değişince codegen yeniden çalışır.
- (+) Tek-nokta interceptor: tenant izolasyonu (X-Tenant) ve token yenileme her istekte tutarlı.
- (−) AntD bundle büyük (~840 kB); kod bölme/rota lazy-load ileride optimize edilecek (bloklayıcı değil).
- (−) Refresh localStorage'da (XSS yüzeyi); rotasyon+iptal azaltır, httpOnly cookie ileride.
- **Kapsam dışı:** zengin veri ekranları/OEE panosu (S6), WebSocket canlı (S7), Playwright
  E2E (S7), Docker frontend servisi/wildcard TLS (Faz 5).
