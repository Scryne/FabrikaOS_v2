import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';
import type { AbonelikCevap } from '@/modules/abonelik/hooks';

import { AbonelikSayfasi } from './AbonelikSayfasi';

const VERI: AbonelikCevap = {
  plan: { kod: 'temel', ad: 'Temel', koltuk_limiti: 10 },
  durum: 'deneme',
  baslangic_tarihi: '2026-07-01T00:00:00Z',
  bitis_tarihi: null,
  koltuk: { limit: 10, kullanilan: 8 },
  moduller: [
    { kod: 'uretim', ad: 'Üretim & OEE', acik: true, kaynak: 'plan' },
    { kod: 'ai', ad: 'AI Tahminleri', acik: false, kaynak: 'plan' },
    { kod: 'kalite', ad: 'Kalite', acik: true, kaynak: 'hak' },
  ],
  ozellikler: [{ kod: 'mobil-api', ad: 'Mobil API', acik: false, deneysel: true }],
};

function ekrana(veri: AbonelikCevap) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, staleTime: 60_000 } },
  });
  qc.setQueryData(['abonelik'], veri);
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AbonelikSayfasi />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AbonelikSayfasi', () => {
  it('plan adı, koltuk kullanımı ve modül matrisi render edilir', () => {
    ekrana(VERI);
    expect(screen.getByText('Temel')).toBeInTheDocument();
    expect(screen.getByText('8 / 10 aktif kullanıcı')).toBeInTheDocument();
    expect(screen.getByText('Üretim & OEE')).toBeInTheDocument();
    expect(screen.getByText('AI Tahminleri')).toBeInTheDocument();
    // Açık/kapalı rozetleri: 2 açık modül + 1 kapalı modül + 1 kapalı özellik.
    expect(screen.getAllByText('Açık')).toHaveLength(2);
    expect(screen.getAllByText('Kapalı')).toHaveLength(2);
    // Override kaynağı işaretlenir.
    expect(screen.getByText('Özel hak')).toBeInTheDocument();
    // Deneysel özellik rozeti.
    expect(screen.getByText('Deneysel')).toBeInTheDocument();
  });

  it('sınırsız koltukta progress yerine sınırsız etiketi', () => {
    ekrana({
      ...VERI,
      plan: { kod: 'kurumsal', ad: 'Kurumsal', koltuk_limiti: null },
      koltuk: { limit: null, kullanilan: 42 },
    });
    expect(screen.getByText('Sınırsız koltuk')).toBeInTheDocument();
  });
});
