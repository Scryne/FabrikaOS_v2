import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { BildirimZili } from './BildirimZili';

const okunduMutate = vi.fn();
const tumunuMutate = vi.fn();

vi.mock('./hooks', () => ({
  useBildirimOzet: () => ({
    isLoading: false,
    data: {
      okunmamis: 2,
      toplam: 5,
      son: [
        {
          id: 11,
          olay_turu: 'stok.kritik',
          baslik: 'Stok kritik eşiğin altında: HM-1',
          govde: '',
          veri: { kaynak_tur: 'malzeme', kaynak_id: 7 },
          onem: 'uyari',
          okundu: false,
          okundu_tarihi: null,
          olusturma_tarihi: new Date().toISOString(),
        },
      ],
    },
  }),
  useBildirimOkundu: () => ({ mutate: okunduMutate }),
  useTumunuOkundu: () => ({ mutate: tumunuMutate }),
}));

describe('BildirimZili', () => {
  it('okunmamış rozetini gösterir; panelde son bildirim listelenir ve tıklama okundu işaretler', () => {
    render(
      <MemoryRouter>
        <BildirimZili />
      </MemoryRouter>,
    );
    // Rozet: okunmamış sayısı.
    expect(screen.getByText('2')).toBeInTheDocument();

    // Zile tıkla → panel açılır, bildirim satırı görünür.
    fireEvent.click(screen.getByRole('button', { name: 'Bildirimler' }));
    const satir = screen.getByText('Stok kritik eşiğin altında: HM-1');
    expect(satir).toBeInTheDocument();

    // Satıra tıkla → okundu mutasyonu çağrılır (derin bağlantı navigate eder).
    fireEvent.click(satir);
    expect(okunduMutate).toHaveBeenCalledWith(11);
  });

  it('tümünü okundu aksiyonu mutasyonu tetikler', () => {
    render(
      <MemoryRouter>
        <BildirimZili />
      </MemoryRouter>,
    );
    fireEvent.click(screen.getByRole('button', { name: 'Bildirimler' }));
    fireEvent.click(screen.getByText('Tümünü okundu say'));
    expect(tumunuMutate).toHaveBeenCalled();
  });
});
