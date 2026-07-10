import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import '@/i18n';

import { usePlatformAuthStore } from './store';
import { TenantListesi } from './TenantListesi';

const TENANTLAR = [
  {
    id: 1,
    slug: 'alfa',
    ad: 'Alfa Fabrika',
    aktif: true,
    plan_kodu: 'kurumsal',
    abonelik_durum: 'deneme',
    koltuk_limiti: null,
    koltuk_kullanilan: 3,
    olusturma_tarihi: '2026-07-01T00:00:00Z',
  },
  {
    id: 2,
    slug: 'beta',
    ad: 'Beta Fabrika',
    aktif: false,
    plan_kodu: 'temel',
    abonelik_durum: 'deneme',
    koltuk_limiti: 10,
    koltuk_kullanilan: 5,
    olusturma_tarihi: '2026-07-02T00:00:00Z',
  },
];

function jsonCevap(govde: unknown): Response {
  return new Response(JSON.stringify(govde), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  });
}

describe('TenantListesi', () => {
  beforeEach(() => {
    usePlatformAuthStore.getState().ayarlaOturum('access', {
      id: 1,
      eposta: 'root@fabrikaos.test',
      ad_soyad: 'Kök',
      son_giris_tarihi: null,
    });
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        jsonCevap({
          success: true,
          message: 'tamam',
          data: TENANTLAR,
          meta: { sayfa: 1, adet: 20, toplam: 2 },
        }),
      ),
    );
  });

  it('tenant satırlarını plan/durum/koltuk bilgisiyle listeler', async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <TenantListesi />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText('alfa')).toBeInTheDocument();
    expect(screen.getByText('Beta Fabrika')).toBeInTheDocument();
    expect(screen.getByText('kurumsal')).toBeInTheDocument();
    expect(screen.getByText('Askıda')).toBeInTheDocument(); // beta askıda
    expect(screen.getByText(/3 \/ Sınırsız/)).toBeInTheDocument(); // sınırsız koltuk
    expect(screen.getByText(/5 \/ 10/)).toBeInTheDocument();
  });
});
