import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { IzinListesi } from './IzinListesi';

vi.mock('./hooks', () => {
  const sahteMutasyon = () => ({ mutateAsync: vi.fn(), isPending: false });
  return {
    useIzinler: () => ({
      data: {
        veri: [
          {
            id: 1,
            kod: 'IZ-2026-000001',
            personel_id: 7,
            izin_turu: 'yillik',
            baslangic_tarihi: '2026-08-01',
            bitis_tarihi: '2026-08-05',
            gun_sayisi: 5,
            aciklama: '',
            durum: 'onay_bekliyor',
            talep_eden_kullanici_id: null,
            onaylayan_kullanici_id: null,
            onay_tarihi: null,
            red_nedeni: '',
            olusturma_tarihi: '2026-07-04T08:00:00Z',
          },
        ],
        meta: { sayfa: 1, adet: 20, toplam: 1 },
      },
      isPending: false,
      isError: false,
    }),
    useIzin: () => ({ data: undefined }),
    useIzinPano: () => ({ data: [], isPending: false, isError: false }),
    useIzinOlustur: sahteMutasyon,
    useIzinDurumAksiyon: sahteMutasyon,
  };
});

describe('IzinListesi', () => {
  it('izin taleplerini durum + tür rozetleriyle listeler', () => {
    render(
      <MemoryRouter>
        <IzinListesi />
      </MemoryRouter>,
    );
    expect(screen.getByText('IZ-2026-000001')).toBeInTheDocument();
    // durum 'onay_bekliyor' → "Onay bekliyor", tür 'yillik' → "Yıllık"
    expect(screen.getByText('Onay bekliyor')).toBeInTheDocument();
    expect(screen.getByText('Yıllık')).toBeInTheDocument();
  });

  it('ik:yaz izni yokken "Yeni izin talebi" butonu gizli', () => {
    render(
      <MemoryRouter>
        <IzinListesi />
      </MemoryRouter>,
    );
    expect(screen.queryByText('Yeni izin talebi')).not.toBeInTheDocument();
  });
});
