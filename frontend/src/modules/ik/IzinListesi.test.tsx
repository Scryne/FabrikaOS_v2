import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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
            personel_ad: 'Selin Kaya',
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
    useIzinPano: () => ({
      data: [
        {
          id: 2,
          kod: 'IZ-2026-000002',
          personel_id: 9,
          personel_ad: 'Kaan Ateş',
          izin_turu: 'mazeret',
          baslangic_tarihi: '2026-08-03',
          bitis_tarihi: '2026-08-04',
          gun_sayisi: 2,
          aciklama: '',
          durum: 'taslak',
          talep_eden_kullanici_id: null,
          onaylayan_kullanici_id: null,
          onay_tarihi: null,
          red_nedeni: '',
          olusturma_tarihi: '2026-07-04T08:00:00Z',
        },
      ],
      isPending: false,
      isError: false,
    }),
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

  it('personeli kayıt numarasıyla değil adıyla gösterir (tablo + pano)', async () => {
    const u = userEvent.setup();
    render(
      <MemoryRouter>
        <IzinListesi />
      </MemoryRouter>,
    );
    expect(screen.getByText('Selin Kaya')).toBeInTheDocument();
    expect(screen.queryByText('#7')).not.toBeInTheDocument();

    await u.click(screen.getByText('Pano'));
    expect(await screen.findByText(/Kaan Ateş · 2/)).toBeInTheDocument();
    expect(screen.queryByText(/#9/)).not.toBeInTheDocument();
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
