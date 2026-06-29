import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { Kullanici } from '@/store/authStore';
import { useAuthStore } from '@/store/authStore';

import { ApiHata, istek, istekSayfali } from './client';
import { refreshOku, refreshSakla } from './jeton';
import { tenantSakla } from './tenant';

const KULLANICI: Kullanici = {
  id: 1,
  eposta: 'admin@alfa.test',
  ad_soyad: 'Yönetici',
  roller: ['admin'],
  izinler: ['uretim:oku'],
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

describe('api client interceptor', () => {
  beforeEach(() => {
    localStorage.clear();
    useAuthStore.getState().temizle();
    tenantSakla('alfa');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('her isteğe X-Tenant ve Bearer enjekte eder', async () => {
    useAuthStore.getState().ayarlaOturum('access1', KULLANICI);
    const fetchMock = vi.fn().mockResolvedValue(jsonCevap(200, basariliZarf({ deger: 1 })));
    vi.stubGlobal('fetch', fetchMock);

    await istek('GET', '/api/v1/deneme');

    const [, secenek] = fetchMock.mock.calls[0]!;
    const headers = (secenek as RequestInit).headers as Record<string, string>;
    expect(headers['X-Tenant']).toBe('alfa');
    expect(headers['Authorization']).toBe('Bearer access1');
  });

  it('başarılı zarfın data alanını döndürür', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonCevap(200, basariliZarf({ deger: 42 })));
    vi.stubGlobal('fetch', fetchMock);

    const data = await istek<{ deger: number }>('GET', '/api/v1/deneme');
    expect(data).toEqual({ deger: 42 });
  });

  it('istekSayfali data listesini ve meta’yı birlikte döndürür', async () => {
    const govde = {
      success: true,
      message: 'tamam',
      data: [{ id: 1 }, { id: 2 }],
      meta: { sayfa: 2, adet: 20, toplam: 137 },
    };
    const fetchMock = vi.fn().mockResolvedValue(jsonCevap(200, govde));
    vi.stubGlobal('fetch', fetchMock);

    const { veri, meta } = await istekSayfali<{ id: number }>('/api/v1/makineler?sayfa=2&adet=20');
    expect(veri).toHaveLength(2);
    expect(meta).toEqual({ sayfa: 2, adet: 20, toplam: 137 });
  });

  it('401’de refresh ile yeni access alır ve orijinali tekrar dener', async () => {
    useAuthStore.getState().ayarlaOturum('access1', KULLANICI);
    refreshSakla('refresh1');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonCevap(401, { success: false, message: 'süresi doldu' }))
      .mockResolvedValueOnce(jsonCevap(200, jetonZarf('access2', 'refresh2')))
      .mockResolvedValueOnce(jsonCevap(200, basariliZarf({ deger: 7 })));
    vi.stubGlobal('fetch', fetchMock);

    const data = await istek<{ deger: number }>('GET', '/api/v1/korumali');

    expect(data).toEqual({ deger: 7 });
    expect(useAuthStore.getState().access).toBe('access2');
    expect(refreshOku()).toBe('refresh2');
    expect(fetchMock).toHaveBeenCalledTimes(3);
    // Tekrar denenen istek YENİ bearer'ı taşımalı.
    const [, ucuncuSecenek] = fetchMock.mock.calls[2]!;
    const headers = (ucuncuSecenek as RequestInit).headers as Record<string, string>;
    expect(headers['Authorization']).toBe('Bearer access2');
  });

  it('refresh de başarısızsa oturumu düşürür ve hata fırlatır', async () => {
    useAuthStore.getState().ayarlaOturum('access1', KULLANICI);
    refreshSakla('refresh1');
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonCevap(401, { success: false, message: 'süresi doldu' }))
      .mockResolvedValueOnce(jsonCevap(401, { success: false, message: 'refresh geçersiz' }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(istek('GET', '/api/v1/korumali')).rejects.toBeInstanceOf(ApiHata);
    expect(useAuthStore.getState().girisYapildi).toBe(false);
    expect(refreshOku()).toBeNull();
  });

  it('refresh token yokken 401 → oturum düşer', async () => {
    useAuthStore.getState().ayarlaOturum('access1', KULLANICI);
    const fetchMock = vi.fn().mockResolvedValue(jsonCevap(401, { success: false, message: 'yok' }));
    vi.stubGlobal('fetch', fetchMock);

    await expect(istek('GET', '/api/v1/korumali')).rejects.toBeInstanceOf(ApiHata);
    expect(useAuthStore.getState().girisYapildi).toBe(false);
    // Refresh denemesi yapılmamalı (yalnız 1 istek).
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
