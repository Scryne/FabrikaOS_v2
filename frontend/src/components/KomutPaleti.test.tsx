import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import '@/i18n';
import { useAuthStore } from '@/store/authStore';

import { KomutPaleti } from './KomutPaleti';

// İçerik araması (S27-A): sunucu yanıtı taklit; 2+ karakterde kayıt grupları listelenir.
vi.mock('@/modules/deneyim/hooks', () => ({
  useIcerikArama: (q: string) => ({
    isFetching: false,
    data:
      q.trim().length >= 2 && 'rulman'.startsWith(q.trim().toLocaleLowerCase('tr'))
        ? [
            {
              tur: 'malzeme',
              kayitlar: [{ id: 7, baslik: 'Rulman 6204', alt: 'MLZ-001', yol: '/malzemeler/7' }],
            },
          ]
        : [],
  }),
}));

function kur(izinler: string[]) {
  useAuthStore.setState({ izinler: new Set(izinler) });
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter>
        <KomutPaleti acik kapat={() => {}} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('KomutPaleti', () => {
  it('yalnız yetkili sayfaları listeler (RBAC süzgeci)', () => {
    kur(['uretim:oku']);
    expect(screen.getByText('Pano')).toBeInTheDocument(); // izin gerekmez
    expect(screen.getByText('Makineler')).toBeInTheDocument(); // uretim:oku
    expect(screen.queryByText('Kullanıcılar')).not.toBeInTheDocument(); // kullanici:oku yok
  });

  it('arama sonuçları süzer', async () => {
    const u = userEvent.setup();
    kur(['uretim:oku', 'stok:oku']);
    await u.type(screen.getByPlaceholderText('Sayfa ya da kayıt ara…'), 'makine');
    expect(screen.getByText('Makineler')).toBeInTheDocument();
    expect(screen.queryByText('Malzemeler')).not.toBeInTheDocument();
  });

  it('2+ karakterde kayıtları grup başlığıyla listeler ve kayda gider', async () => {
    const u = userEvent.setup();
    kur(['stok:oku']);
    await u.type(screen.getByPlaceholderText('Sayfa ya da kayıt ara…'), 'rulman');
    expect(await screen.findByText('Rulman 6204', {}, { timeout: 2000 })).toBeInTheDocument();
    expect(screen.getByText('Malzemeler')).toBeInTheDocument(); // grup başlığı
    expect(screen.getByText('MLZ-001')).toBeInTheDocument();
  });
});
