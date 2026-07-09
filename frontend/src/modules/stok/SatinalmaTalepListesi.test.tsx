import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { SatinalmaTalepListesi } from './SatinalmaTalepListesi';

vi.mock('./hooks', () => {
  const sahteMutasyon = () => ({ mutateAsync: vi.fn(), isPending: false });
  return {
    useTalepler: () => ({
      data: {
        veri: [
          {
            id: 1,
            kod: 'ST-2026-000001',
            baslik: 'Rulman alımı',
            aciklama: '',
            durum: 'taslak',
            para_birimi: 'TRY',
            talep_eden_kullanici_id: 1,
            onaylayan_kullanici_id: null,
            onay_tarihi: null,
            red_nedeni: null,
            tahmini_toplam: 300,
            olusturma_tarihi: '2026-06-30T10:00:00Z',
          },
        ],
        meta: { sayfa: 1, adet: 20, toplam: 1 },
      },
      isPending: false,
      isError: false,
    }),
    useTalep: () => ({ data: undefined }),
    useTalepPano: () => ({ data: [], isPending: false, isError: false }),
    useSatinalmaOzet: () => ({
      data: {
        onay_bekleyen: 0,
        taslak: 1,
        onaylandi: 0,
        reddedildi: 0,
        toplam: 1,
        durum_dagilimi: [],
      },
      isPending: false,
    }),
    useTalepOlustur: sahteMutasyon,
    useTalepDurumAksiyon: sahteMutasyon,
    useMalzemeler: () => ({ data: { veri: [], meta: { sayfa: 1, adet: 100, toplam: 0 } } }),
  };
});

describe('SatinalmaTalepListesi', () => {
  it('talepleri sunucu-taraflı tabloda listeler', () => {
    render(
      <MemoryRouter>
        <SatinalmaTalepListesi />
      </MemoryRouter>,
    );
    expect(screen.getByText('ST-2026-000001')).toBeInTheDocument();
    expect(screen.getByText('Rulman alımı')).toBeInTheDocument();
  });
});
