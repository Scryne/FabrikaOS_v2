import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App } from 'antd';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { Onaylarim } from './Onaylarim';

const mutate = vi.fn();

vi.mock('./hooks', () => ({
  useOnayKutusu: () => ({
    isPending: false,
    isError: false,
    data: {
      kendi_sayimlarim: 1,
      kalemler: [
        {
          tur: 'izin_talebi',
          id: 4,
          kod: 'IZ-2026-000004',
          baslik: 'Kaan Ateş · yillik',
          ozet: '01.12.2026 – 05.12.2026 · 5 gün',
          talep_eden: 'Zeynep Arslan',
          tarih: '2026-10-28T09:00:00Z',
          onay_yolu: '/izin-talepleri/4/onayla',
          red_yolu: '/izin-talepleri/4/reddet',
          red_gerekce_zorunlu: true,
          detay_yolu: '/izin-talepleri?kayit=4',
        },
        {
          tur: 'sayim',
          id: 9,
          kod: 'SAY-2026-0009',
          baslik: 'Sayım farkları · SAY-2026-0009',
          ozet: '',
          talep_eden: 'Ayşe Demir',
          tarih: '2026-10-30T09:00:00Z',
          onay_yolu: '/sayimlar/9/onayla',
          red_yolu: null,
          red_gerekce_zorunlu: false,
          detay_yolu: '/sayimlar/9',
        },
      ],
    },
  }),
  useOnayEylemi: () => ({ mutate, isPending: false, variables: undefined }),
}));

function kur() {
  return render(
    <App>
      <MemoryRouter>
        <Onaylarim />
      </MemoryRouter>
    </App>,
  );
}

describe('Onaylarim', () => {
  it('kalemleri türüyle listeler, görev ayrımı notunu gösterir, redsiz kalemde reddet yok', () => {
    kur();
    expect(screen.getByText('Kaan Ateş · yillik')).toBeInTheDocument();
    expect(screen.getByText(/başka bir yetkili onaylamalı/)).toBeInTheDocument();
    const sayimSatiri = screen.getByText('Sayım farkları · SAY-2026-0009').closest('tr')!;
    expect(within(sayimSatiri).queryByRole('button', { name: /Reddet/ })).toBeNull();
    expect(within(sayimSatiri).getByRole('button', { name: /Onayla/ })).toBeInTheDocument();
  });

  it('zorunlu red gerekçesi girilmeden red gönderilemez', async () => {
    const u = userEvent.setup({ delay: null });
    kur();
    await u.click(screen.getByRole('button', { name: 'Reddet: IZ-2026-000004' }));
    const dialog = await screen.findByRole('dialog');
    const tamam = within(dialog)
      .getAllByRole('button', { name: /Reddet/ })
      .at(-1)!;
    expect(tamam).toBeDisabled();
    await u.type(within(dialog).getByRole('textbox'), 'Bütçe dönemi kapandı');
    expect(tamam).toBeEnabled();
    await u.click(tamam);
    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({ eylem: 'red', neden: 'Bütçe dönemi kapandı' }),
      expect.anything(),
    );
  });
});
