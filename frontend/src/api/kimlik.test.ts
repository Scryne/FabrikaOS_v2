import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/store/authStore';

import { girisYap, oturumBaslat } from './kimlik';
import { refreshOku, refreshSakla } from './jeton';
import { tenantOku } from './tenant';

function jsonCevap(durum: number, data: unknown): Response {
  return new Response(JSON.stringify({ success: true, message: 't', data }), {
    status: durum,
    headers: { 'content-type': 'application/json' },
  });
}

const KULLANICI = {
  id: 5,
  eposta: 'admin@alfa.test',
  ad_soyad: 'Yönetici',
  roller: ['admin'],
  izinler: ['uretim:oku', 'isemri:yaz'],
};

/** URL'e göre yanıt seçen fetch mock'u. */
function yonlendir(harita: Array<[string, () => Response]>) {
  return vi.fn(async (url: unknown) => {
    const u = String(url);
    for (const [parca, yap] of harita) if (u.includes(parca)) return yap();
    return new Response('bulunamadı', { status: 404 });
  });
}

describe('kimlik servisi', () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.getState().temizle();
  });
  afterEach(() => vi.unstubAllGlobals());

  it('girisYap: firma kodunu saklar, token alır, kullanıcıyı kurar', async () => {
    vi.stubGlobal(
      'fetch',
      yonlendir([
        ['/kimlik/token', () => jsonCevap(200, { access_token: 'a1', refresh_token: 'r1' })],
        ['/kimlik/ben', () => jsonCevap(200, KULLANICI)],
      ]),
    );

    await girisYap('alfa', 'admin@alfa.test', 'Parola123!');

    expect(tenantOku()).toBe('alfa');
    expect(refreshOku()).toBe('r1');
    const s = useAuthStore.getState();
    expect(s.access).toBe('a1');
    expect(s.kullanici?.eposta).toBe('admin@alfa.test');
    expect(s.girisYapildi).toBe(true);
    expect(s.izinVar('isemri:yaz')).toBe(true);
  });

  it('oturumBaslat: saklı refresh varsa sessiz giriş yapar', async () => {
    refreshSakla('r-eski');
    vi.stubGlobal(
      'fetch',
      yonlendir([
        ['/kimlik/yenile', () => jsonCevap(200, { access_token: 'a2', refresh_token: 'r2' })],
        ['/kimlik/ben', () => jsonCevap(200, KULLANICI)],
      ]),
    );

    const sonuc = await oturumBaslat();

    expect(sonuc).toBe(true);
    expect(useAuthStore.getState().access).toBe('a2');
    expect(refreshOku()).toBe('r2');
  });

  it('oturumBaslat: refresh yoksa false döner, istek atmaz', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);

    const sonuc = await oturumBaslat();

    expect(sonuc).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
