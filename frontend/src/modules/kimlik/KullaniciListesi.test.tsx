import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { KullaniciListesi } from './KullaniciListesi';

vi.mock('./hooks', () => ({
  useKullanicilar: () => ({
    data: {
      veri: [
        {
          id: 1,
          eposta: 'admin@alfa.test',
          ad_soyad: 'Tenant Yöneticisi',
          aktif: true,
          roller: ['admin'],
        },
        {
          id: 2,
          eposta: 'izleyici@alfa.test',
          ad_soyad: 'Salt Okur',
          aktif: false,
          roller: ['izleyici'],
        },
      ],
      meta: { sayfa: 1, adet: 20, toplam: 2 },
    },
    isPending: false,
    isError: false,
  }),
}));

vi.mock('./KullaniciFormu', () => ({ KullaniciFormu: () => null }));

describe('KullaniciListesi', () => {
  it('kullanıcıları rol rozetleri ve durumla listeler', () => {
    render(
      <MemoryRouter>
        <KullaniciListesi />
      </MemoryRouter>,
    );
    expect(screen.getByText('admin@alfa.test')).toBeInTheDocument();
    expect(screen.getByText('Tenant Yöneticisi')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
    expect(screen.getByText('Aktif')).toBeInTheDocument();
    expect(screen.getByText('Pasif')).toBeInTheDocument();
  });
});
