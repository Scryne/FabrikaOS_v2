import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { UrunListesi } from './UrunListesi';

vi.mock('./hooks', () => ({
  useUrunler: () => ({
    data: {
      veri: [
        {
          id: 1,
          kod: 'URN-001',
          ad: 'Çelik Gövde',
          birim: 'adet',
          aciklama: '',
          aktif: true,
          olusturma_tarihi: '2026-07-15T08:00:00Z',
        },
      ],
      meta: { sayfa: 1, adet: 20, toplam: 1 },
    },
    isPending: false,
    isError: false,
  }),
  useUrunOlustur: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUrunGuncelle: () => ({ mutate: vi.fn(), isPending: false, variables: undefined }),
}));

vi.mock('./ReceteCekmecesi', () => ({ ReceteCekmecesi: () => null }));

describe('UrunListesi', () => {
  it('ürünleri kod, ad ve birim ile listeler', () => {
    render(
      <MemoryRouter>
        <UrunListesi />
      </MemoryRouter>,
    );
    expect(screen.getByText('URN-001')).toBeInTheDocument();
    expect(screen.getByText('Çelik Gövde')).toBeInTheDocument();
    expect(screen.getByText('adet')).toBeInTheDocument();
  });

  it('her satırda reçete (BOM) aksiyonu vardır', () => {
    render(
      <MemoryRouter>
        <UrunListesi />
      </MemoryRouter>,
    );
    expect(screen.getByRole('button', { name: /Reçete/ })).toBeInTheDocument();
  });
});
