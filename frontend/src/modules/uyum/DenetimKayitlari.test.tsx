import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
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
        {
          id: 13,
          kullanici_id: 4,
          kullanici_eposta: 'yeni@alfa.test',
          eylem: 'yeni_eylem',
          kaynak: 'yeni_kaynak_turu',
          kaynak_id: null,
          request_id: null,
          ip_adresi: null,
          detay: {},
          olusturma_tarihi: '2026-07-30T10:16:00Z',
        },
      ],
      meta: { sayfa: 1, adet: 20, toplam: 2 },
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
    // Kaynak ve eylem kodu değil okunur adla görünür (ham ``stok_hareketi``/``olustur`` değil).
    const tablo = within(document.querySelector('.ant-table-tbody') as HTMLElement);
    expect(tablo.getByText('Stok hareketi')).toBeInTheDocument();
    expect(tablo.getByText('Oluştur')).toBeInTheDocument();
    expect(tablo.queryByText('stok_hareketi')).toBeNull();
    expect(tablo.queryByText('olustur')).toBeNull();

    await u.click(screen.getByText('depo@alfa.test'));

    // Çekmece açılır; ham detay JSON'ı görünür (denetim izinin tam içeriği).
    expect(await screen.findByText(/req-abc/)).toBeInTheDocument();
    expect(screen.getByText(/"miktar": 25/)).toBeInTheDocument();
    // Kayıt numarası kendi satırında (kaynak adına "#88" diye yapışık değil).
    const cekmece = within(document.querySelector('.ant-drawer-body') as HTMLElement);
    expect(cekmece.getByText('Stok hareketi')).toBeInTheDocument();
    expect(cekmece.getByText('88')).toBeInTheDocument();
    expect(cekmece.queryByText(/#88/)).toBeNull();
  });

  it('etiketi henüz olmayan kodu gizlemez, olduğu gibi gösterir (denetim izi eksiksiz)', () => {
    ekranaBas();
    const tablo = within(document.querySelector('.ant-table-tbody') as HTMLElement);
    expect(tablo.getByText('yeni_kaynak_turu')).toBeInTheDocument();
    expect(tablo.getByText('yeni_eylem')).toBeInTheDocument();
  });

  it('düzenleme/silme aksiyonu sunmaz (append-only defter)', () => {
    ekranaBas();
    expect(screen.queryByRole('button', { name: /sil/i })).toBeNull();
    expect(screen.queryByRole('button', { name: /düzenle/i })).toBeNull();
  });
});
