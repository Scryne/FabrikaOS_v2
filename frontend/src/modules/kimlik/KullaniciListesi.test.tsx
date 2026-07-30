import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { useAuthStore } from '@/store/authStore';

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
  useKullaniciOzet: () => ({
    data: { toplam: 2, aktif: 1, pasif: 1, rol_sayisi: 2, rol_dagilimi: [] },
    isPending: false,
  }),
}));

vi.mock('./KullaniciFormu', () => ({
  KullaniciFormu: ({
    acik,
    duzenlenen,
  }: {
    acik: boolean;
    duzenlenen?: { eposta: string } | null;
  }) => (acik ? <div data-testid="kullanici-form">{duzenlenen?.eposta ?? 'yeni'}</div> : null),
}));

function ekrana() {
  return render(
    <MemoryRouter>
      <KullaniciListesi />
    </MemoryRouter>,
  );
}

describe('KullaniciListesi', () => {
  beforeEach(() => useAuthStore.getState().temizle());

  it('kullanıcıları rol rozetleri ve durumla listeler', () => {
    ekrana();
    expect(screen.getByText('admin@alfa.test')).toBeInTheDocument();
    expect(screen.getByText('Tenant Yöneticisi')).toBeInTheDocument();
    expect(screen.getByText('admin')).toBeInTheDocument();
    expect(screen.getByText('Aktif')).toBeInTheDocument();
    expect(screen.getByText('Pasif')).toBeInTheDocument();
  });

  it('kullanici:yaz ile satıra tıklama düzenleme formunu seçili kullanıcıyla açar', () => {
    useAuthStore.getState().ayarlaOturum('access', {
      id: 1,
      eposta: 'admin@alfa.test',
      ad_soyad: 'Yönetici',
      roller: ['admin'],
      izinler: ['kullanici:yaz'],
      iki_asama_aktif: false,
    });
    ekrana();
    fireEvent.click(screen.getByText('izleyici@alfa.test'));
    expect(screen.getByTestId('kullanici-form')).toHaveTextContent('izleyici@alfa.test');
  });

  it('yazma izni yokken satır tıklaması form açmaz', () => {
    ekrana();
    fireEvent.click(screen.getByText('izleyici@alfa.test'));
    expect(screen.queryByTestId('kullanici-form')).not.toBeInTheDocument();
  });
});
