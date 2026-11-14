import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
    {
      alt_grup_id: 41,
      sira: 1,
      degerler: [10, 10.01, 9.99],
      uygunsuzluk_id: null,
      uygunsuzluk_kod: null,
      zaman: '2026-10-31T10:00:00Z',
      xbar: 10,
      r: 0.01,
      kayitli_ihlaller: [],
    },
    {
      alt_grup_id: 42,
      sira: 2,
      degerler: [10.03, 10.035, 10.025],
      uygunsuzluk_id: null,
      uygunsuzluk_kod: null,
      zaman: '2026-10-31T11:00:00Z',
      xbar: 10.03,
      r: 0.01,
      kayitli_ihlaller: [],
    },
  ],
  ihlaller: [{ kart: 'xbar', kural: 1, indeks: 1, aciklama: '3σ dışında' }],
  yetenek: { sigma_ic: 0.006, cp: 2.78, cpk: 1.11 },
  uyarilar: [],
};

const olustur = vi.fn().mockResolvedValue({ id: 99 });
vi.mock('./hooks', () => ({
  useUygunsuzlukOlustur: () => ({ mutateAsync: olustur, isPending: false }),
  useKaliteMakineSecenekleri: () => ({ data: [], isPending: false }),
}));
vi.mock('@/modules/kimlik/hooks', () => ({ useFirmaSecenekleri: () => ({ data: [] }) }));
vi.mock('@/modules/isemri/hooks', () => ({ useKullaniciSecenekleri: () => ({ data: [] }) }));

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

  it('ihlal satırından uygunsuzluk açılır: form ihlal bilgisiyle dolu, kayıt alt gruba bağlı', async () => {
    kur(['kalite:oku', 'kalite:yaz']);
    await userEvent.setup().click(screen.getByRole('button', { name: 'Uygunsuzluk aç' }));
    expect(
      await screen.findByDisplayValue('SPC ihlali: Mil çapı · alt grup #2'),
    ).toBeInTheDocument();
    const aciklama = screen.getByLabelText(/Açıklama/) as HTMLTextAreaElement;
    expect(aciklama.value).toContain('X̄ kartı kural 1');
    expect(aciklama.value).toContain('10,030; 10,035; 10,025 mm');
    await userEvent.setup().click(screen.getByRole('button', { name: 'Kaydet' }));
    expect(olustur).toHaveBeenCalledWith(
      expect.objectContaining({ kaynak_spc_alt_grup_id: 42, onem: 'yuksek' }),
    );
  });

  it('yalnız okuma izniyle ölçüm girişi ve sabitleme gizlenir', () => {
    kur(['kalite:oku']);
    expect(screen.queryByLabelText('1. ölçüm')).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Limitleri sabitle/ })).not.toBeInTheDocument();
  });
});
