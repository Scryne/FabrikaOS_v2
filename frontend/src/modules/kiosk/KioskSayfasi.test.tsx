import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { KioskSayfasi } from './KioskSayfasi';

vi.mock('@/modules/ikiz/hooks', () => ({
  useIkizDurum: () => ({
    data: {
      saat: 24,
      baslangic: '2026-07-07T12:00:00Z',
      bitis: '2026-07-08T12:00:00Z',
      ozet: {
        toplam_makine: 3,
        durumlar: { calisiyor: 2, ariza: 1 },
        kayit_sayisi: 4,
        toplam_adet: 1250,
        saglam_adet: 1200,
        fire_orani: 0.04,
        oee: 0.815,
        acik_ariza: 1,
      },
      dugumler: [
        {
          makine_id: 1,
          makine_kod: 'MAK-1',
          makine_ad: 'Pres Hattı',
          durum: 'calisiyor',
          x: 20,
          y: 30,
          bolge: '',
          oee: 0.9,
          toplam_adet: 800,
          son_veri_zamani: '2026-07-08T10:00:00Z',
        },
      ],
      yerlesmemis: [
        { makine_id: 2, makine_kod: 'MAK-2', makine_ad: 'Kaynak Robotu', durum: 'ariza' },
      ],
    },
    isPending: false,
    isError: false,
    dataUpdatedAt: Date.now(),
  }),
}));

function ciz() {
  return render(
    <MemoryRouter>
      <KioskSayfasi />
    </MemoryRouter>,
  );
}

describe('KioskSayfasi', () => {
  it('tesis KPI kartlarını büyük değerlerle gösterir', () => {
    ciz();
    expect(screen.getByText('Üretim (24s)')).toBeInTheDocument();
    expect(screen.getByText('1.250')).toBeInTheDocument();
    expect(screen.getByText('%82')).toBeInTheDocument(); // tesis OEE
    expect(screen.getByText('2/3')).toBeInTheDocument(); // çalışan makine
  });

  it('yerleşimden bağımsız tüm makineleri karo olarak listeler', () => {
    ciz();
    expect(screen.getByText('MAK-1')).toBeInTheDocument();
    expect(screen.getByText('MAK-2')).toBeInTheDocument(); // yerleşmemiş de görünür
    expect(screen.getByText('Arıza')).toBeInTheDocument();
  });

  it('salt-okunur: ekranda hiçbir buton yok', () => {
    ciz();
    expect(screen.queryAllByRole('button')).toHaveLength(0);
  });
});
