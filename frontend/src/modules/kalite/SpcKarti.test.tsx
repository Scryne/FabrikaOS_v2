import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App } from 'antd';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import '@/i18n';
import { useAuthStore } from '@/store/authStore';

import { SpcKarti } from './SpcKarti';
import type { SpcKart } from './spcHooks';

vi.mock('@/components/grafik/EGrafik', () => ({ EGrafik: () => <div data-testid="grafik" /> }));

const kart: SpcKart = {
  karakteristik_id: 7,
  plan_id: 3,
  ad: 'Mil çapı',
  birim: 'mm',
  nominal: 10,
  alt_tolerans: 9.95,
  ust_tolerans: 10.05,
  cihaz_id: null,
  alt_grup_boyutu: 3,
  limitler_sabit: false,
  limitler: {
    n: 3,
    alt_grup_sayisi: 2,
    xbar_cl: 10,
    xbar_ucl: 10.02,
    xbar_lcl: 9.98,
    r_cl: 0.01,
    r_ucl: 0.026,
    r_lcl: 0,
  },
  noktalar: [
    { sira: 1, zaman: '2026-10-31T10:00:00Z', xbar: 10, r: 0.01, kayitli_ihlaller: [] },
    { sira: 2, zaman: '2026-10-31T11:00:00Z', xbar: 10.03, r: 0.01, kayitli_ihlaller: [] },
  ],
  ihlaller: [{ kart: 'xbar', kural: 1, indeks: 1, aciklama: '3σ dışında' }],
  yetenek: { sigma_ic: 0.006, cp: 2.78, cpk: 1.11 },
  uyarilar: [],
};

vi.mock('./spcHooks', () => ({
  useSpcKart: () => ({ data: kart, isPending: false }),
  useOlcumGir: () => ({ mutate: vi.fn(), isPending: false }),
  useLimitSabitle: () => ({ mutate: vi.fn(), isPending: false }),
}));

function kur(izinler: string[]) {
  useAuthStore.setState({ izinler: new Set(izinler) });
  return render(
    <App>
      <MemoryRouter initialEntries={['/karakteristikler/7/spc']}>
        <Routes>
          <Route path="/karakteristikler/:id/spc" element={<SpcKarti />} />
        </Routes>
      </MemoryRouter>
    </App>,
  );
}

describe('SpcKarti', () => {
  it('kartları, Cpk ve ihlali gösterir; yazma izniyle n alanlı ölçüm formu açılır', () => {
    kur(['kalite:oku', 'kalite:yaz']);
    expect(screen.getByRole('heading', { name: 'Mil çapı' })).toBeInTheDocument();
    expect(screen.getAllByTestId('grafik')).toHaveLength(2);
    expect(screen.getByText('1,11')).toBeInTheDocument();
    expect(screen.getByText('3σ dışında bir nokta')).toBeInTheDocument();
    // n = 3 → üç ölçüm girişi
    expect(screen.getByLabelText('3. ölçüm')).toBeInTheDocument();
    expect(screen.queryByLabelText('4. ölçüm')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Limitleri sabitle/ })).toBeInTheDocument();
  });

  it('yalnız okuma izniyle ölçüm girişi ve sabitleme gizlenir', () => {
    kur(['kalite:oku']);
    expect(screen.queryByLabelText('1. ölçüm')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Limitleri sabitle/ })).not.toBeInTheDocument();
  });
});
