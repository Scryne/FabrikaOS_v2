import { expect, request as pwRequest, test } from '@playwright/test';
import type { Page } from '@playwright/test';

/**
 * Kritik E2E: gerçek-zaman canlı güncelleme (S7 kabul kriteri).
 *
 * Bir kullanıcı makineler ekranını açıkken, **başka bir istemci** (API) bir makinenin
 * durumunu değiştirir. WebSocket olayı listeyi geçersizleştirir ve satır **manuel yenileme
 * olmadan** yeni durumu gösterir. Bu, makine→olay→pano canlı akışını uçtan uca doğrular.
 */

const API = process.env.E2E_API ?? 'http://localhost:8000/api/v1';
const TENANT = 'demo';
const EPOSTA = 'demo@demo.test';
const PAROLA = 'Demo12345!';

const ETIKET: Record<string, string> = {
  calisiyor: 'Çalışıyor',
  durdu: 'Durdu',
  bakimda: 'Bakımda',
  ariza: 'Arıza',
};

async function girisYap(page: Page): Promise<void> {
  await page.goto('/giris');
  await page.getByLabel(/firma kodu/i).fill(TENANT);
  await page.getByLabel(/e-posta/i).fill(EPOSTA);
  await page.getByLabel(/^parola/i).fill(PAROLA);
  await page.getByRole('button', { name: /giriş yap/i }).click();
  await page.waitForURL((u) => new URL(u).pathname === '/');
}

test('başka istemcinin makine durum değişikliği listede canlı görünür', async ({ page }) => {
  await girisYap(page);
  // Menüden gezin (tam reload yok → oturum/WS korunur).
  await page.getByRole('menuitem', { name: 'Makineler' }).click();
  await page.waitForURL((u) => new URL(u).pathname === '/makineler');

  const satir = page.locator('tr', { hasText: 'MAK-A1' });
  await expect(satir).toBeVisible();

  // İkinci istemci (API) — MAK-A1 durumunu mevcuttan FARKLI bir değere çevirir.
  const rc = await pwRequest.newContext();
  const tokenCevap = await rc.post(`${API}/kimlik/token`, {
    form: { username: EPOSTA, password: PAROLA },
    headers: { 'X-Tenant': TENANT },
  });
  const access = (await tokenCevap.json()).data.access_token as string;
  const auth = { 'X-Tenant': TENANT, Authorization: `Bearer ${access}` };

  const liste = await (await rc.get(`${API}/makineler?arama=MAK-A1`, { headers: auth })).json();
  const makine = liste.data[0] as { id: number; durum: string };
  const hedef = makine.durum === 'calisiyor' ? 'ariza' : 'calisiyor';

  await rc.patch(`${API}/makineler/${makine.id}/durum`, { data: { durum: hedef }, headers: auth });
  await rc.dispose();

  // Manuel yenileme YOK — WS olayı listeyi tazeler ve satır yeni durumu gösterir.
  await expect(page.locator('tr', { hasText: 'MAK-A1' }).getByText(ETIKET[hedef]!)).toBeVisible();
});
