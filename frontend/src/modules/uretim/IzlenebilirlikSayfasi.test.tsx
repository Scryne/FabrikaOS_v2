import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { IzlenebilirlikSayfasi } from './IzlenebilirlikSayfasi';

vi.mock('./hooks', () => ({
  useIzlenebilirlik: (lot: string) => ({
    data:
      lot.length > 0
        ? {
            lot_no: lot,
            is_emirleri: [
              {
                id: 1,
                kod: 'IE-2026-000001',
                durum: 'kapandi',
                urun_id: 1,
                miktar: 10,
                kapanis_tarihi: '2026-07-15T10:00:00Z',
              },
            ],
            uretim: [
              {
                makine_id: 5,
                makine_kod: 'CNC-1',
                kayit_sayisi: 2,
                toplam_adet: 100,
                saglam_adet: 95,
                ilk_zaman: '2026-07-15T08:00:00Z',
                son_zaman: '2026-07-15T09:00:00Z',
              },
            ],
            tuketilen_malzemeler: [
              {
                malzeme_id: 3,
                malzeme_kod: 'SAC-2MM',
                malzeme_ad: 'Sac 2mm',
                miktar: 20,
                is_emri_kod: 'IE-2026-000001',
              },
            ],
          }
        : undefined,
    isFetching: false,
    isError: false,
  }),
}));

describe('IzlenebilirlikSayfasi', () => {
  it('lot girilmeden önce yönlendirici boş durum gösterir', () => {
    render(
      <MemoryRouter>
        <IzlenebilirlikSayfasi />
      </MemoryRouter>,
    );
    expect(screen.getByText('Lot sorgusu bekleniyor')).toBeInTheDocument();
  });

  it('lot sorgusunda ileri/geri zincir listelenir', () => {
    render(
      <MemoryRouter>
        <IzlenebilirlikSayfasi />
      </MemoryRouter>,
    );
    fireEvent.change(screen.getByPlaceholderText('Lot numarası girin (ör. LOT-2026-001)'), {
      target: { value: 'LOT-1' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'Sorgula' }));
    expect(screen.getAllByText('IE-2026-000001').length).toBeGreaterThan(0);
    expect(screen.getByText('SAC-2MM')).toBeInTheDocument();
    expect(screen.getByText('CNC-1')).toBeInTheDocument();
  });
});
