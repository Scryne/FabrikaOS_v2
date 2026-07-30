import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { App as AntApp } from 'antd';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { DenetimKayitlari } from './DenetimKayitlari';

vi.mock('./hooks', () => ({
  useDenetimKayitlari: () => ({
    data: {
      veri: [
        {
          id: 12,
          kullanici_id: 3,
          kullanici_eposta: 'depo@alfa.test',
          eylem: 'olustur',
          kaynak: 'stok_hareketi',
          kaynak_id: '88',
          request_id: 'req-abc',
          ip_adresi: '10.0.0.9',
          detay: { miktar: 25, birim: 'kg' },
          olusturma_tarihi: '2026-07-30T10:15:00Z',
        },
      ],
      meta: { sayfa: 1, adet: 20, toplam: 1 },
    },
    isPending: false,
    isError: false,
  }),
  useDenetimKaynaklari: () => ({ data: ['stok_hareketi', 'kimlik'] }),
}));

function ekranaBas() {
  render(
    <AntApp>
      <MemoryRouter>
        <DenetimKayitlari />
      </MemoryRouter>
    </AntApp>,
  );
}

describe('DenetimKayitlari', () => {
  it('kaydı listeler ve satır detayını çekmecede ham JSON ile gösterir', async () => {
    const u = userEvent.setup();
    ekranaBas();

    expect(screen.getByText('depo@alfa.test')).toBeInTheDocument();
    expect(screen.getAllByText('stok_hareketi').length).toBeGreaterThan(0);

    await u.click(screen.getByText('depo@alfa.test'));

    // Çekmece açılır; ham detay JSON'ı görünür (denetim izinin tam içeriği).
    expect(await screen.findByText(/req-abc/)).toBeInTheDocument();
    expect(screen.getByText(/"miktar": 25/)).toBeInTheDocument();
  });

  it('düzenleme/silme aksiyonu sunmaz (append-only defter)', () => {
    ekranaBas();
    expect(screen.queryByRole('button', { name: /sil/i })).toBeNull();
    expect(screen.queryByRole('button', { name: /düzenle/i })).toBeNull();
  });
});
