import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { UygunsuzlukListesi } from './UygunsuzlukListesi';

vi.mock('./hooks', () => {
  const sahteMutasyon = () => ({ mutateAsync: vi.fn(), isPending: false });
  return {
    useUygunsuzluklar: () => ({
      data: {
        veri: [
          {
            id: 1,
            kod: 'UY-2026-000001',
            baslik: 'Yüzey çiziği',
            aciklama: '',
            kaynak_kontrol_id: null,
            makine_id: null,
            onem: 'yuksek',
            durum: 'acik',
            kok_neden: '',
            acan_kullanici_id: null,
            sorumlu_kullanici_id: null,
            dogrulama_notu: '',
            kapanis_tarihi: null,
            olusturma_tarihi: '2026-07-01T10:00:00Z',
          },
        ],
        meta: { sayfa: 1, adet: 20, toplam: 1 },
      },
      isPending: false,
      isError: false,
    }),
    useUygunsuzluk: () => ({ data: undefined }),
    useUygunsuzlukOlustur: sahteMutasyon,
    useCapaDurum: sahteMutasyon,
    useAksiyonEkle: sahteMutasyon,
    useAksiyonGuncelle: sahteMutasyon,
  };
});

describe('UygunsuzlukListesi', () => {
  it('uygunsuzlukları durum + önem rozetleriyle listeler', () => {
    render(
      <MemoryRouter>
        <UygunsuzlukListesi />
      </MemoryRouter>,
    );
    expect(screen.getByText('UY-2026-000001')).toBeInTheDocument();
    expect(screen.getByText('Yüzey çiziği')).toBeInTheDocument();
    // durum 'acik' → "Açık", önem 'yuksek' → "Yüksek" rozetleri
    expect(screen.getByText('Açık')).toBeInTheDocument();
    expect(screen.getByText('Yüksek')).toBeInTheDocument();
  });

  it('kalite:yaz izni yokken "Yeni uygunsuzluk" butonu gizli', () => {
    // Varsayılan authStore izinleri boş → yazma aksiyonu görünmez (izin-duyarlı).
    render(
      <MemoryRouter>
        <UygunsuzlukListesi />
      </MemoryRouter>,
    );
    expect(screen.queryByText('Yeni uygunsuzluk')).not.toBeInTheDocument();
  });
});
