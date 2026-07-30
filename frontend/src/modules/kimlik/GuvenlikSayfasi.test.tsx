import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App as AntApp } from 'antd';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';
import { oturumlariGetir, oturumSonlandir } from '@/api/kimlik';
import { useAuthStore } from '@/store/authStore';

import { GuvenlikSayfasi } from './GuvenlikSayfasi';

vi.mock('@/api/kimlik', () => ({
  oturumlariGetir: vi.fn(),
  oturumSonlandir: vi.fn().mockResolvedValue(undefined),
  ikiAsamaKapat: vi.fn().mockResolvedValue(undefined),
  ikiAsamaKur: vi.fn().mockResolvedValue({ sir: 'JBSWY3DPEHPK3PXP', otpauth_uri: 'otpauth://x' }),
  ikiAsamaEtkinlestir: vi.fn().mockResolvedValue(['AAAA-BBBB']),
}));

function oturumAc(ikiAsamaAktif: boolean) {
  useAuthStore.getState().ayarlaOturum('access', {
    id: 1,
    eposta: 'admin@alfa.test',
    ad_soyad: 'Yönetici',
    roller: ['admin'],
    izinler: [],
    iki_asama_aktif: ikiAsamaAktif,
  });
}

function ekranaBas() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={qc}>
      <AntApp>
        <MemoryRouter>
          <GuvenlikSayfasi />
        </MemoryRouter>
      </AntApp>
    </QueryClientProvider>,
  );
}

describe('GuvenlikSayfasi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(oturumlariGetir).mockResolvedValue([
      {
        id: 7,
        ip_adresi: '10.0.0.5',
        istemci: 'Mozilla/5.0 Chrome/120',
        olusturma_tarihi: '2026-07-30T08:00:00Z',
        son_kullanim: '2026-07-30T09:30:00Z',
        bitis: '2026-08-06T08:00:00Z',
      },
    ]);
  });

  it('2FA kapalıyken kurulum düğmesi, açıkken kapatma düğmesi gösterir', async () => {
    oturumAc(false);
    ekranaBas();
    expect(await screen.findByRole('button', { name: /2FA kurulumunu başlat/i })).toBeVisible();

    oturumAc(true);
    ekranaBas();
    expect((await screen.findAllByRole('button', { name: /2FA kapat/i })).length).toBeGreaterThan(
      0,
    );
  });

  it('aktif oturumları listeler ve uzaktan sonlandırır', async () => {
    oturumAc(false);
    const u = userEvent.setup();
    ekranaBas();

    expect(await screen.findByText('10.0.0.5')).toBeInTheDocument();

    await u.click(screen.getByRole('button', { name: /sonlandır/i }));
    // TanStack Query v5 mutationFn'e ikinci argüman (bağlam) geçirir → yalnız ilki denetlenir.
    await waitFor(() => expect(vi.mocked(oturumSonlandir).mock.calls[0]?.[0]).toBe(7));
  });
});
