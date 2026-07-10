import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiHata } from '@/api/client';

import { platformIstek, platformRefreshOku, platformRefreshSakla } from './api';
import { usePlatformAuthStore } from './store';

const YONETICI = {
  id: 1,
  eposta: 'root@fabrikaos.test',
  ad_soyad: 'Kök Yönetici',
  son_giris_tarihi: null,
};

function jsonCevap(durum: number, govde: unknown): Response {
  return new Response(JSON.stringify(govde), {
    status: durum,
    headers: { 'content-type': 'application/json' },
  });
}

function basariliZarf(data: unknown): unknown {
  return { success: true, message: 'tamam', data };
}

function jetonZarf(access: string, refresh: string): unknown {
  return basariliZarf({ access_token: access, refresh_token: refresh, token_tipi: 'bearer' });
}

describe('platform api istemcisi', () => {
  beforeEach(() => {
    localStorage.clear();
    usePlatformAuthStore.getState().temizle();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('Bearer enjekte eder ama X-Tenant başlığı ASLA göndermez', async () => {
    usePlatformAuthStore.getState().ayarlaOturum('access1', YONETICI);
    const fetchMock = vi.fn().mockResolvedValue(jsonCevap(200, basariliZarf({ deger: 1 })));
    vi.stubGlobal('fetch', fetchMock);

    await platformIstek('GET', '/api/v1/platform/tenantlar');

    const [, secenek] = fetchMock.mock.calls[0]!;
    const headers = (secenek as RequestInit).headers as Record<string, string>;
    expect(headers['Authorization']).toBe('Bearer access1');
    expect(headers['X-Tenant']).toBeUndefined(); // control-plane tenant'tan bağımsız
  });

  it('401’de /platform/kimlik/yenile ile yeni access alır ve tekrar dener', async () => {
    usePlatformAuthStore.getState().ayarlaOturum('access1', YONETICI);
    platformRefreshSakla('refresh1');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonCevap(401, { success: false, message: 'süresi doldu' }))
      .mockResolvedValueOnce(jsonCevap(200, jetonZarf('access2', 'refresh2')))
      .mockResolvedValueOnce(jsonCevap(200, basariliZarf({ deger: 7 })));
    vi.stubGlobal('fetch', fetchMock);

    const data = await platformIstek<{ deger: number }>('GET', '/api/v1/platform/tenantlar');

    expect(data).toEqual({ deger: 7 });
    expect(usePlatformAuthStore.getState().access).toBe('access2');
    expect(platformRefreshOku()).toBe('refresh2');
    // Yenileme isteği platform kimlik ucuna gitmeli.
    const [yenileYol] = fetchMock.mock.calls[1]!;
    expect(String(yenileYol)).toContain('/api/v1/platform/kimlik/yenile');
  });

  it('refresh de düşerse platform oturumunu düşürür ve hata fırlatır', async () => {
    usePlatformAuthStore.getState().ayarlaOturum('access1', YONETICI);
    platformRefreshSakla('refresh1');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonCevap(401, { success: false, message: 'süresi doldu' }))
      .mockResolvedValueOnce(jsonCevap(401, { success: false, message: 'refresh geçersiz' }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(platformIstek('GET', '/api/v1/platform/tenantlar')).rejects.toBeInstanceOf(
      ApiHata,
    );
    expect(usePlatformAuthStore.getState().girisYapildi).toBe(false);
    expect(platformRefreshOku()).toBeNull();
  });

  it('tenant düzleminin refresh anahtarına dokunmaz (ayrık depolama)', async () => {
    localStorage.setItem('fabrikaos.refresh', 'tenant-refresh');
    usePlatformAuthStore.getState().ayarlaOturum('access1', YONETICI);
    const fetchMock = vi.fn().mockResolvedValue(jsonCevap(401, { success: false, message: 'x' }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(platformIstek('GET', '/api/v1/platform/tenantlar')).rejects.toBeInstanceOf(
      ApiHata,
    );
    expect(localStorage.getItem('fabrikaos.refresh')).toBe('tenant-refresh');
  });
});
