import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App as AntApp } from 'antd';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';
import { useAuthStore } from '@/store/authStore';

import { DisPortalSayfasi } from './DisPortalSayfasi';
import { sadeceDisKullanici } from './hooks';

vi.mock('./hooks', async (orijinalImport) => {
  const orijinal = await orijinalImport<typeof import('./hooks')>();
  return {
    ...orijinal,
    useDisDurum: () => ({
      data: {
        firma_ad: 'Dış Portal A.Ş.',
        toplam: 3,
        acik: 2,
        durum_dagilimi: [{ durum: 'acik', adet: 2 }],
        son_talepler: [],
      },
    }),
    useDisTalepler: () => ({
      data: {
        veri: [
          {
            id: 1,
            kod: 'TL-2026-000001',
            baslik: 'Sevkiyat gecikmesi',
            aciklama: 'Sipariş #42 gecikti',
            tur: 'destek',
            oncelik: 'orta',
            durum: 'inceleniyor',
            olusturma_tarihi: '2026-07-10T10:00:00Z',
            guncelleme_tarihi: '2026-07-10T11:00:00Z',
          },
        ],
        meta: { sayfa: 1, adet: 20, toplam: 1 },
      },
      isPending: false,
      isError: false,
    }),
    useDisTalepOlustur: () => ({ mutateAsync: vi.fn(), isPending: false }),
  };
});

describe('DisPortalSayfasi', () => {
  beforeEach(() => {
    useAuthStore.getState().temizle();
    useAuthStore.getState().ayarlaOturum('access', {
      id: 5,
      eposta: 'portal@musteri.test',
      ad_soyad: 'Portal Kullanıcısı',
      roller: ['dis-panel'],
      izinler: ['dis:erisim'],
    });
  });

  it('hafif kabuk: marka + firma adı + sekmeler + müşteri-dili durum', () => {
    render(
      <AntApp>
        <MemoryRouter>
          <DisPortalSayfasi />
        </MemoryRouter>
      </AntApp>,
    );

    expect(screen.getByText('FabrikaOS Müşteri Portalı')).toBeInTheDocument();
    expect(screen.getByText('Dış Portal A.Ş.')).toBeInTheDocument(); // markalama alanı
    expect(screen.getByRole('tab', { name: 'Taleplerim' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Yeni Talep' })).toBeInTheDocument();

    expect(screen.getByText('TL-2026-000001')).toBeInTheDocument();
    // Müşteri-dili durum adı: "inceleniyor" değil "İşleme alındı".
    expect(screen.getByText('İşleme alındı')).toBeInTheDocument();
    expect(screen.queryByText('inceleniyor')).not.toBeInTheDocument();
    expect(screen.getByText('2 açık talep')).toBeInTheDocument();
  });
});

describe('sadeceDisKullanici (giriş yönlendirme kararı)', () => {
  it('tek izni dis:erisim olan kullanıcı → true', () => {
    expect(sadeceDisKullanici(['dis:erisim'])).toBe(true);
  });
  it('iç izni olan kullanıcı (admin dahil) → false', () => {
    expect(sadeceDisKullanici(['dis:erisim', 'uretim:oku'])).toBe(false);
    expect(sadeceDisKullanici(['uretim:oku'])).toBe(false);
    expect(sadeceDisKullanici([])).toBe(false);
  });
});
