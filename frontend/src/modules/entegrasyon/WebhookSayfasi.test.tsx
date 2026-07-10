import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App as AntApp } from 'antd';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';
import { useAuthStore } from '@/store/authStore';

import { WebhookSayfasi } from './WebhookSayfasi';

vi.mock('./hooks', () => {
  // vi.mock hoist edilir: fabrika dışı değişkenlere erişemez — yardımcı içeride tanımlı.
  const bosMutasyon = () => ({
    mutate: vi.fn(),
    mutateAsync: vi.fn(),
    isPending: false,
    variables: undefined,
  });
  return {
    API_KAPSAMLARI: ['uretim:oku', 'stok:oku', 'satinalma:oku'],
    useWebhooklar: () => ({
      data: {
        veri: [
          {
            id: 1,
            ad: 'ERP köprüsü',
            url: 'https://erp.ornek.test/hook',
            gizli_anahtar: 'whs_abcd…wxyz',
            olay_turleri: ['is_emri.kapandi', 'stok.kritik'],
            aktif: true,
            olusturma_tarihi: '2026-07-10T10:00:00Z',
          },
          {
            id: 2,
            ad: 'Tüm olay dinleyicisi',
            url: 'https://hepsi.ornek.test/hook',
            gizli_anahtar: 'whs_efgh…stuv',
            olay_turleri: [],
            aktif: false,
            olusturma_tarihi: '2026-07-10T10:00:00Z',
          },
        ],
        meta: { sayfa: 1, adet: 20, toplam: 2 },
      },
      isPending: false,
      isError: false,
    }),
    useOlayTurleri: () => ({ data: [{ kod: 'is_emri.kapandi', aciklama: 'İş emri kapandı' }] }),
    useTeslimatlar: () => ({
      data: { veri: [], meta: { sayfa: 1, adet: 20, toplam: 0 } },
      isPending: false,
      isError: false,
    }),
    useApiAnahtarlari: () => ({
      data: { veri: [], meta: { sayfa: 1, adet: 20, toplam: 0 } },
      isPending: false,
      isError: false,
    }),
    useWebhookOlustur: bosMutasyon,
    useWebhookGuncelle: bosMutasyon,
    useWebhookSil: bosMutasyon,
    useAnahtarYenile: bosMutasyon,
    useYenidenDene: bosMutasyon,
    useApiAnahtarOlustur: bosMutasyon,
    useApiAnahtarGuncelle: bosMutasyon,
    useApiAnahtarSil: bosMutasyon,
  };
});

function oturum(izinler: string[]) {
  useAuthStore.getState().ayarlaOturum('access', {
    id: 1,
    eposta: 'admin@alfa.test',
    ad_soyad: 'Yönetici',
    roller: ['admin'],
    izinler,
  });
}

function ekrana() {
  return render(
    <AntApp>
      <MemoryRouter>
        <WebhookSayfasi />
      </MemoryRouter>
    </AntApp>,
  );
}

describe('WebhookSayfasi', () => {
  beforeEach(() => useAuthStore.getState().temizle());

  it('üç sekme + abonelik satırları (maskeli anahtar, olay çipleri) render edilir', () => {
    oturum(['entegrasyon:oku', 'entegrasyon:yaz']);
    ekrana();

    expect(screen.getByRole('tab', { name: 'Webhook Abonelikleri' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'Teslimat Günlüğü' })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: 'API Anahtarları' })).toBeInTheDocument();

    expect(screen.getByText('ERP köprüsü')).toBeInTheDocument();
    expect(screen.getByText('whs_abcd…wxyz')).toBeInTheDocument(); // maskeli — tam değer yok
    expect(screen.getByText('is_emri.kapandi')).toBeInTheDocument();
    expect(screen.getByText('Tüm olaylar')).toBeInTheDocument(); // boş liste = tümü
    expect(screen.getByRole('button', { name: /Yeni webhook/ })).toBeInTheDocument();
  });

  it('entegrasyon:yaz yoksa yazma aksiyonları görünmez', () => {
    oturum(['entegrasyon:oku']);
    ekrana();

    expect(screen.queryByRole('button', { name: /Yeni webhook/ })).not.toBeInTheDocument();
    expect(screen.queryByText('Anahtarı yenile')).not.toBeInTheDocument();
    expect(screen.queryByText('Sil')).not.toBeInTheDocument();
  });
});
