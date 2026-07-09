import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { KazaListesi } from './KazaListesi';

vi.mock('./hooks', () => {
  const sahteMutasyon = () => ({ mutateAsync: vi.fn(), isPending: false });
  return {
    useKazalar: () => ({
      data: {
        veri: [
          {
            id: 1,
            kod: 'KZ-2026-000001',
            tur: 'ramak_kala',
            olay_tarihi: '2026-07-04T08:00:00Z',
            yer: 'Kaynak Hattı',
            aciklama: '',
            agirlik: 'orta',
            kaybedilen_gun: 0,
            yaralanma_turu: '',
            personel_id: null,
            makine_id: null,
            raporlayan_kullanici_id: null,
            olusturma_tarihi: '2026-07-04T08:00:00Z',
          },
        ],
        meta: { sayfa: 1, adet: 20, toplam: 1 },
      },
      isPending: false,
      isError: false,
    }),
    useIsgOzet: () => ({
      data: {
        gunluk_kazasiz: 30,
        bu_yil_kaza: 1,
        ramak_kala: 1,
        toplam_kayip_gun: 0,
        acik_risk: 0,
        yuksek_risk: 0,
        toplam_risk: 0,
        risk_matrisi: [],
      },
      isPending: false,
    }),
    useKazaOlustur: sahteMutasyon,
  };
});

describe('KazaListesi', () => {
  it('kazaları tür + ağırlık rozetleriyle listeler', () => {
    render(
      <MemoryRouter>
        <KazaListesi />
      </MemoryRouter>,
    );
    expect(screen.getByText('KZ-2026-000001')).toBeInTheDocument();
    expect(screen.getByText('Ramak kala')).toBeInTheDocument();
    expect(screen.getByText('Orta')).toBeInTheDocument();
  });

  it('isg:yaz izni yokken "Yeni iş kazası" butonu gizli', () => {
    render(
      <MemoryRouter>
        <KazaListesi />
      </MemoryRouter>,
    );
    expect(screen.queryByText('Yeni iş kazası')).not.toBeInTheDocument();
  });
});
