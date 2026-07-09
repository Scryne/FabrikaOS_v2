import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';
import { useAuthStore } from '@/store/authStore';

import { KomutPaleti } from './KomutPaleti';

function kur(izinler: string[]) {
  useAuthStore.setState({ izinler: new Set(izinler) });
  return render(
    <MemoryRouter>
      <KomutPaleti acik kapat={() => {}} />
    </MemoryRouter>,
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
    await u.type(screen.getByPlaceholderText('Sayfa ara ya da git…'), 'makine');
    expect(screen.getByText('Makineler')).toBeInTheDocument();
    expect(screen.queryByText('Malzemeler')).not.toBeInTheDocument();
  });
});
