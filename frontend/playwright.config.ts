import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E yapılandırması (S7 — ilk kritik E2E).
 *
 * Önkoşul: çalışan yığın — backend (:8000, WS dahil), frontend dev sunucusu ve
 * provizyonlanmış+seed'li ``demo`` tenant. Origin'ler env ile geçilebilir:
 *   E2E_BASE (frontend, vars. http://localhost:5173) · E2E_API (vars. .../api/v1)
 * CORS dev'de 5173'e izinli olduğundan frontend'i 5173'te çalıştırın ya da CORS'a
 * geçerli origin'i ekleyin.
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: process.env.E2E_BASE ?? 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
});
