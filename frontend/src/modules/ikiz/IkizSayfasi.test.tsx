import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { IkizSayfasi } from './IkizSayfasi';

vi.mock('./hooks', () => ({
  useIkizDurum: () => ({
    data: {
      saat: 24,
      baslangic: '2026-07-07T12:00:00Z',
      bitis: '2026-07-08T12:00:00Z',
      ozet: {
        toplam_makine: 3,
        durumlar: { calisiyor: 1, ariza: 1, durdu: 1 },
        kayit_sayisi: 1,
        toplam_adet: 400,
        saglam_adet: 380,
        fire_orani: 0.05,
        oee: 0.83,
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
          bolge: 'Hat A',
          oee: 0.83,
          toplam_adet: 400,
          son_veri_zamani: '2026-07-08T10:00:00Z',
        },
        {
          makine_id: 2,
          makine_kod: 'MAK-2',
          makine_ad: 'Kaynak Robotu',
          durum: 'ariza',
          x: 60,
          y: 30,
          bolge: '',
          oee: null,
          toplam_adet: 0,
          son_veri_zamani: null,
        },
      ],
      yerlesmemis: [{ makine_id: 3, makine_kod: 'MAK-3', makine_ad: 'Paketleme', durum: 'durdu' }],
    },
    isPending: false,
    isError: false,
  }),
  useYerlesimKaydet: () => ({ mutate: vi.fn(), isPending: false }),
}));

function ciz() {
  return render(
    <MemoryRouter>
      <IkizSayfasi />
    </MemoryRouter>,
  );
}

describe('IkizSayfasi', () => {
  it('şemadaki makine düğümlerini kodlarıyla çizer', () => {
    ciz();
    expect(screen.getByText('MAK-1')).toBeInTheDocument();
    expect(screen.getByText('MAK-2')).toBeInTheDocument();
    // Yerleşmemiş makine şemada çizilmez.
    expect(screen.queryByText('MAK-3')).not.toBeInTheDocument();
  });

  it('düğüme tıklayınca yan panelde detay gösterir', () => {
    ciz();
    fireEvent.click(screen.getByText('MAK-1'));
    expect(screen.getByText('Pres Hattı')).toBeInTheDocument();
    expect(screen.getByText('%83')).toBeInTheDocument();
    expect(screen.getByText('Hat A')).toBeInTheDocument();
    expect(screen.getByText('Makine sayfası')).toBeInTheDocument();
  });

  it('uretim:yaz izni yokken Düzenle butonu gizli, Kiosk modu görünür', () => {
    ciz();
    expect(screen.queryByText('Düzenle')).not.toBeInTheDocument();
    expect(screen.getByText('Kiosk modu')).toBeInTheDocument();
  });
});
