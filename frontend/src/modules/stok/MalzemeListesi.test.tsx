import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { MalzemeListesi } from './MalzemeListesi';

vi.mock('./hooks', () => {
  const sahteMutasyon = () => ({ mutateAsync: vi.fn(), isPending: false });
  return {
    useMalzemeler: () => ({
      data: {
        veri: [
          {
            id: 1,
            kod: 'MLZ-1',
            ad: 'Rulman 6203',
            birim: 'adet',
            kategori: '',
            mevcut_miktar: 4,
            min_stok: 0,
            max_stok: null,
            kritik_stok: 5,
            aktif: true,
            kritik: true,
          },
        ],
        meta: { sayfa: 1, adet: 20, toplam: 1 },
      },
      isPending: false,
      isError: false,
    }),
    useMalzemeOlustur: sahteMutasyon,
    useMalzemeGuncelle: sahteMutasyon,
    useStokHareketEkle: sahteMutasyon,
  };
});

describe('MalzemeListesi', () => {
  it('malzemeleri sunucu-taraflı tabloda listeler', () => {
    render(
      <MemoryRouter>
        <MalzemeListesi />
      </MemoryRouter>,
    );
    expect(screen.getByText('MLZ-1')).toBeInTheDocument();
    expect(screen.getByText('Rulman 6203')).toBeInTheDocument();
  });
});
