import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import '@/i18n';

import { PlatformKorunanRota } from './PlatformKorunanRota';
import { usePlatformAuthStore } from './store';

function ekrana(baslangic: string) {
  return render(
    <MemoryRouter initialEntries={[baslangic]}>
      <Routes>
        <Route path="/platform/giris" element={<div>PLATFORM GIRIS</div>} />
        <Route element={<PlatformKorunanRota />}>
          <Route path="/platform" element={<div>PLATFORM ICERIK</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('PlatformKorunanRota', () => {
  beforeEach(() => {
    localStorage.clear();
    usePlatformAuthStore.getState().temizle();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('oturum ve saklı refresh yokken /platform/giris’e yönlendirir', async () => {
    ekrana('/platform');
    // Sessiz giriş (refresh yok → istek atmadan) tamamlanınca yönlendirme yapılır.
    expect(await screen.findByText('PLATFORM GIRIS')).toBeInTheDocument();
    expect(screen.queryByText('PLATFORM ICERIK')).not.toBeInTheDocument();
  });

  it('platform oturumu varken korunan içeriği gösterir', () => {
    usePlatformAuthStore.getState().ayarlaOturum('access', {
      id: 1,
      eposta: 'root@fabrikaos.test',
      ad_soyad: 'Kök',
      son_giris_tarihi: null,
    });
    ekrana('/platform');
    expect(screen.getByText('PLATFORM ICERIK')).toBeInTheDocument();
  });
});
