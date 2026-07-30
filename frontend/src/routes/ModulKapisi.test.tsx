import { beforeEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';
import type { ModullerCevap } from '@/modules/abonelik/hooks';
import type { Kullanici } from '@/store/authStore';
import { useAuthStore } from '@/store/authStore';

import { ModulKapisi } from './ModulKapisi';

function kullanici(izinler: string[]): Kullanici {
  return {
    id: 1,
    eposta: 'a@alfa.test',
    ad_soyad: 'A',
    roller: ['admin'],
    izinler,
    iki_asama_aktif: false,
  };
}

const VERI: ModullerCevap = {
  moduller: [
    { kod: 'uretim', ad: 'Üretim', acik: true, kaynak: 'plan' },
    { kod: 'ai', ad: 'AI Tahminleri', acik: false, kaynak: 'plan' },
  ],
  ozellikler: [],
};

function ekrana(modul: string, veri?: ModullerCevap) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 60_000 } },
  });
  if (veri) qc.setQueryData(['moduller'], veri);
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <ModulKapisi modul={modul}>
          <div>MODUL ICERIGI</div>
        </ModulKapisi>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ModulKapisi (entitlement rota kapısı)', () => {
  beforeEach(() => useAuthStore.getState().temizle());

  it('modül açıkken içerik render edilir', () => {
    useAuthStore.getState().ayarlaOturum('access', kullanici([]));
    ekrana('uretim', VERI);
    expect(screen.getByText('MODUL ICERIGI')).toBeInTheDocument();
  });

  it('modül kapalıyken upsell boş durumu gösterilir (abonelik:oku ile CTA)', () => {
    useAuthStore.getState().ayarlaOturum('access', kullanici(['abonelik:oku']));
    ekrana('ai', VERI);
    expect(screen.queryByText('MODUL ICERIGI')).not.toBeInTheDocument();
    expect(screen.getByText('Bu modül planınızda kapalı')).toBeInTheDocument();
    expect(screen.getByRole('link')).toHaveAttribute('href', '/abonelik');
  });

  it('abonelik:oku yoksa CTA görünmez ama upsell durur', () => {
    useAuthStore.getState().ayarlaOturum('access', kullanici([]));
    ekrana('ai', VERI);
    expect(screen.getByText('Bu modül planınızda kapalı')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('veri henüz yokken fail-open: içerik gizlenmez (backend zorlar)', () => {
    useAuthStore.getState().ayarlaOturum('access', kullanici([]));
    ekrana('ai'); // sorgu verisi yok
    expect(screen.getByText('MODUL ICERIGI')).toBeInTheDocument();
  });
});
