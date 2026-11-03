import { expect, test } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * Uygulama kabuğu yerleşimi (2026-11-03). jsdom yerleşim hesaplamadığı için gerçek tarayıcıda:
 *
 * - Geniş ekranda yan menü görünüm yüksekliğine yapışık ve kendi içinde kayar; belge yüksekliğini
 *   içerik belirler. Önceden uzun menü (≈2777 px) her sayfayı o boya çekip kısa sayfalarda altı
 *   boş bir kaydırma çıkarıyordu.
 * - Daraltma tetiği çalışır; dar ekranda menü üstte katman olarak açılan çekmecedir.
 *
 * Seed'li ``demo`` tenant ister (README). Hesap env ile değiştirilebilir.
 */

const TENANT = 'demo';
const EPOSTA = process.env.E2E_EPOSTA ?? 'admin@demo.test';
const PAROLA = process.env.E2E_PAROLA ?? 'Demo1234!';

async function girisYap(page: Page): Promise<void> {
  await page.goto('/giris');
  await page.getByLabel(/firma kodu/i).fill(TENANT);
  await page.getByLabel(/e-posta/i).fill(EPOSTA);
  await page.getByLabel(/^parola/i).fill(PAROLA);
  await page.getByRole('button', { name: /giriş yap/i }).click();
  await page.waitForURL((u) => !new URL(u).pathname.startsWith('/giris'));
}

const olc = (page: Page) =>
  page.evaluate(() => {
    const yan = document.querySelector('.ant-layout-sider') as HTMLElement;
    const menu = document.querySelector('.kabuk-yan-menu') as HTMLElement;
    return {
      belge: document.documentElement.scrollHeight,
      gorunum: window.innerHeight,
      yanYukseklik: Math.round(yan.getBoundingClientRect().height),
      yanUst: Math.round(yan.getBoundingClientRect().top),
      menuKayar: menu.scrollHeight > menu.clientHeight,
    };
  });

test.describe('geniş ekran (1440)', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('kısa sayfada belge görünümü aşmaz; menü kendi içinde kayar', async ({ page }) => {
    await girisYap(page);
    await page.goto('/izin-talepleri');
    await page.waitForLoadState('networkidle');
    const r = await olc(page);
    expect(r.yanYukseklik).toBe(r.gorunum);
    expect(r.belge).toBeLessThan(r.gorunum + 200); // içerik kadar, menü kadar değil
    expect(r.menuKayar).toBe(true);

    // Menünün son öğesi menü kaydırılarak erişilebilir (sayfa kaydırılmadan).
    const son = page.locator('.kabuk-yan-menu .ant-menu-item').last();
    await son.scrollIntoViewIfNeeded();
    await expect(son).toBeInViewport();
  });

  test('uzun sayfa kayarken menü yerinde kalır', async ({ page }) => {
    await girisYap(page);
    await page.goto('/pano');
    await page.waitForLoadState('networkidle');
    await page.mouse.wheel(0, 2000);
    await page.waitForTimeout(300);
    expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
    const r = await olc(page);
    expect(Math.abs(r.yanUst)).toBe(0);
    expect(r.yanYukseklik).toBe(r.gorunum);
  });

  test('pencere daralınca menü daralır, tetikle açılır, genişleyince geri gelir', async ({
    page,
  }) => {
    await girisYap(page);
    const yan = page.locator('.ant-layout-sider');
    const tetik = page.locator('.ant-layout-sider-zero-width-trigger');
    await expect(yan).not.toHaveClass(/ant-layout-sider-collapsed/);

    await page.setViewportSize({ width: 900, height: 900 }); // lg kırılımının altı
    await expect(yan).toHaveClass(/ant-layout-sider-collapsed/);
    await tetik.click();
    await expect(yan).not.toHaveClass(/ant-layout-sider-collapsed/);
    await tetik.click();
    await expect(yan).toHaveClass(/ant-layout-sider-collapsed/);

    await page.setViewportSize({ width: 1440, height: 900 });
    await expect(yan).not.toHaveClass(/ant-layout-sider-collapsed/);
    const r = await olc(page);
    expect(r.yanYukseklik).toBe(r.gorunum);
  });
});

test.describe('dar ekran (390)', () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test('menü kapalı başlar, görünüm boyu çekmece olarak açılır ve kendi içinde kayar', async ({
    page,
  }) => {
    await girisYap(page);
    const yan = page.locator('.ant-layout-sider');
    await expect(yan).toHaveClass(/ant-layout-sider-collapsed/);
    await page.locator('.ant-layout-sider-zero-width-trigger').click();
    await expect(yan).not.toHaveClass(/ant-layout-sider-collapsed/);
    const r = await olc(page);
    expect(r.yanYukseklik).toBe(r.gorunum);
    expect(r.menuKayar).toBe(true);
    // Yatay taşma yok.
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      390,
    );
  });
});
