import { beforeEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import '@/i18n';
import type { Kullanici } from '@/store/authStore';
import { useAuthStore } from '@/store/authStore';

import { IzinKapisi, KorunanRota } from './KorunanRota';

const KULLANICI: Kullanici = {
  id: 1,
  eposta: 'a@alfa.test',
  ad_soyad: 'A',
  roller: ['admin'],
  izinler: ['uretim:oku'],
  iki_asama_aktif: false,
};

function ekrana(baslangic: string) {
  return render(
    <MemoryRouter initialEntries={[baslangic]}>
      <Routes>
        <Route path="/giris" element={<div>GIRIS EKRANI</div>} />
        <Route element={<KorunanRota />}>
          <Route path="/korumali" element={<div>KORUMALI ICERIK</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('KorunanRota', () => {
  beforeEach(() => useAuthStore.getState().temizle());

  it('oturum yokken /giris’e yönlendirir', () => {
    ekrana('/korumali');
    expect(screen.getByText('GIRIS EKRANI')).toBeInTheDocument();
    expect(screen.queryByText('KORUMALI ICERIK')).not.toBeInTheDocument();
  });

  it('oturum varken korunan içeriği gösterir', () => {
    useAuthStore.getState().ayarlaOturum('access', KULLANICI);
    ekrana('/korumali');
    expect(screen.getByText('KORUMALI ICERIK')).toBeInTheDocument();
  });
});

describe('IzinKapisi', () => {
  beforeEach(() => useAuthStore.getState().temizle());

  it('izin yoksa Yetkisiz sayfasını gösterir', () => {
    useAuthStore.getState().ayarlaOturum('access', KULLANICI); // izinler: uretim:oku
    render(
      <MemoryRouter>
        <IzinKapisi izin="kullanici:oku">
          <div>GIZLI</div>
        </IzinKapisi>
      </MemoryRouter>,
    );
    expect(screen.queryByText('GIZLI')).not.toBeInTheDocument();
    expect(screen.getByText(/yetkiniz yok/i)).toBeInTheDocument();
  });

  it('izin varsa içeriği gösterir', () => {
    useAuthStore.getState().ayarlaOturum('access', KULLANICI);
    render(
      <MemoryRouter>
        <IzinKapisi izin="uretim:oku">
          <div>GIZLI</div>
        </IzinKapisi>
      </MemoryRouter>,
    );
    expect(screen.getByText('GIZLI')).toBeInTheDocument();
  });
});
