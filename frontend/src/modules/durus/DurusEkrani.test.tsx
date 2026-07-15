import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { DurusEkrani } from './DurusEkrani';

vi.mock('./hooks', () => ({
  DURUS_SINIFLARI: ['planli', 'plansiz'],
  useDurusKayitlari: () => ({
    data: {
      veri: [
        {
          id: 1,
          makine_id: 5,
          neden_id: 9,
          baslangic: '2026-07-15T08:00:00Z',
          bitis: '2026-07-15T08:30:00Z',
          sure_dk: 30,
          aciklama: 'Fikstür ayarı',
          olusturma_tarihi: '2026-07-15T08:31:00Z',
        },
      ],
      meta: { sayfa: 1, adet: 20, toplam: 1 },
    },
    isPending: false,
    isError: false,
  }),
  useDurusNedenleri: () => ({
    data: [{ id: 9, ad: 'Ayar', sinif: 'planli', aktif: true }],
    isPending: false,
  }),
  useVardiyalar: () => ({
    data: [
      { id: 1, ad: 'Gündüz', baslangic_saat: '08:00:00', bitis_saat: '16:00:00', aktif: true },
    ],
    isPending: false,
  }),
  useDurusPareto: () => ({
    data: [{ neden: 'Ayar', sinif: 'planli', toplam_dk: 30, yuzde: 100, kumulatif_yuzde: 100 }],
    isPending: false,
  }),
  useDurusNedeniOlustur: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDurusNedeniGuncelle: () => ({ mutate: vi.fn(), isPending: false, variables: undefined }),
  useVardiyaOlustur: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useVardiyaGuncelle: () => ({ mutate: vi.fn(), isPending: false, variables: undefined }),
}));

vi.mock('./DurusKaydiFormu', () => ({ DurusKaydiFormu: () => null }));

vi.mock('@/modules/uretim/hooks', () => ({
  useMakineSecenekleri: () => ({ data: [{ id: 5, kod: 'CNC-1', ad: 'CNC Torna 1' }] }),
}));

vi.mock('@/components/grafik/EGrafik', () => ({ EGrafik: () => <div data-testid="grafik" /> }));

describe('DurusEkrani', () => {
  it('duruş kayıtlarını makine kodu, neden ve süresiyle listeler', () => {
    render(
      <MemoryRouter>
        <DurusEkrani />
      </MemoryRouter>,
    );
    expect(screen.getByText('CNC-1')).toBeInTheDocument();
    // 'Ayar' hem KPI (en büyük neden) hem kayıt satırında görünür.
    expect(screen.getAllByText('Ayar').length).toBeGreaterThan(0);
    expect(screen.getByText('30.0')).toBeInTheDocument();
  });

  it('KPI şeridi pareto verisinden türetilir (plansız payı %0)', () => {
    render(
      <MemoryRouter>
        <DurusEkrani />
      </MemoryRouter>,
    );
    expect(screen.getByText('30 dk')).toBeInTheDocument();
    expect(screen.getByText('%0')).toBeInTheDocument();
  });

  it('vardiyalar sekmesi saat aralığını gösterir', () => {
    render(
      <MemoryRouter>
        <DurusEkrani baslangicGorunum="vardiyalar" />
      </MemoryRouter>,
    );
    expect(screen.getByText('Gündüz')).toBeInTheDocument();
    expect(screen.getByText('08:00 – 16:00')).toBeInTheDocument();
  });

  it('pareto sekmesine geçilince grafik + kırılım tablosu gelir', () => {
    render(
      <MemoryRouter>
        <DurusEkrani />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByText('Pareto'));
    expect(screen.getByTestId('grafik')).toBeInTheDocument();
    // %100.0 hem pay hem kümülatif sütununda (tek satırlı seri) görünür.
    expect(screen.getAllByText('%100.0').length).toBeGreaterThan(0);
  });
});
