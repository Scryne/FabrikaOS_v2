import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { BakimPlanListesi } from './BakimPlanListesi';

vi.mock('./hooks', () => ({
  BAKIM_TIPLERI: ['onleyici', 'kestirimci', 'periyodik'],
  useBakimPlanlari: () => ({
    data: {
      veri: [
        {
          id: 1,
          makine_id: 5,
          ad: 'Aylık yağlama',
          tip: 'periyodik',
          periyot_gun: 30,
          son_bakim_tarihi: '2026-06-01T08:00:00Z',
          sonraki_bakim_tarihi: '2026-07-01T08:00:00Z',
          aktif: true,
          aciklama: '',
        },
      ],
      meta: { sayfa: 1, adet: 20, toplam: 1 },
    },
    isPending: false,
    isError: false,
  }),
  useBakimPlaniGuncelle: () => ({ mutate: vi.fn(), isPending: false, variables: undefined }),
}));

vi.mock('./BakimPlaniFormu', () => ({
  BakimPlaniFormu: () => null,
}));

vi.mock('@/modules/uretim/hooks', () => ({
  useMakineSecenekleri: () => ({
    data: [{ id: 5, kod: 'CNC-1', ad: 'CNC Torna 1' }],
  }),
}));

describe('BakimPlanListesi', () => {
  it('bakım planlarını makine kodu ve tip rozetiyle listeler', () => {
    render(
      <MemoryRouter>
        <BakimPlanListesi />
      </MemoryRouter>,
    );
    expect(screen.getByText('Aylık yağlama')).toBeInTheDocument();
    expect(screen.getByText('CNC-1')).toBeInTheDocument();
    expect(screen.getByText('Periyodik')).toBeInTheDocument();
  });

  it('geciken sonraki bakımı vurgular', () => {
    render(
      <MemoryRouter>
        <BakimPlanListesi />
      </MemoryRouter>,
    );
    expect(screen.getByText('Gecikti')).toBeInTheDocument();
  });
});
