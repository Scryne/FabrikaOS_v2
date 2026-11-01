import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';
import { useAuthStore } from '@/store/authStore';

import { FaturaDetay } from './FaturaDetay';
import type { Fatura } from './hooks';

const fatura: Fatura = {
  id: 7,
  kod: 'FT-2026-000007',
  tur: 'satis',
  firma_id: 3,
  firma_ad: 'Aksa Makina',
  durum: 'onay_bekliyor',
  fatura_tarihi: '2026-10-01',
  vade_tarihi: '2026-10-31',
  para_birimi: 'TRY',
  ara_toplam: 150.01,
  kdv_toplam: 25,
  genel_toplam: 175.01,
  odenen_tutar: 0,
  acik_tutar: 175.01,
  vadesi_gecti: false,
  aciklama: '',
  iade_nedeni: '',
  iptal_nedeni: '',
  satinalma_siparisi_id: null,
  olusturan_kullanici_id: 11,
  kesen_kullanici_id: null,
  kesim_tarihi: null,
  ettn: '00000000-0000-0000-0000-000000000007',
  senaryo: 'TEMELFATURA',
  gib_durumu: 'gonderilmedi',
  olusturma_tarihi: '2026-10-01T08:00:00Z',
  kalemler: [
    {
      id: 1,
      sira: 1,
      aciklama: 'Sac kesim hizmeti',
      malzeme_id: null,
      miktar: 3,
      birim: 'adet',
      birim_fiyat: 33.335,
      kdv_orani: 20,
      satir_tutari: 100.01,
      kdv_tutari: 20,
    },
  ],
};

vi.mock('@/modules/crm/hooks', () => ({
  useFirmalar: () => ({ data: { veri: [] }, isPending: false }),
}));

vi.mock('./hooks', async (asil) => {
  const gercek = await asil<typeof import('./hooks')>();
  const mut = () => ({ mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false });
  return {
    ...gercek,
    useFatura: () => ({ data: fatura }),
    useFaturaAksiyon: mut,
    useFaturaOlustur: mut,
    useFaturaGuncelle: mut,
    useOdemeOlustur: mut,
    useFaturalar: () => ({ data: { veri: [] } }),
  };
});

function oturum(kullaniciId: number, izinler: string[]) {
  useAuthStore.setState({
    izinler: new Set(izinler),
    kullanici: { id: kullaniciId } as never,
  });
}

function ciz() {
  render(
    <MemoryRouter>
      <FaturaDetay id={7} kapat={() => {}} />
    </MemoryRouter>,
  );
}

describe('FaturaDetay', () => {
  beforeEach(() => useAuthStore.setState({ izinler: new Set(), kullanici: null }));

  it('toplamları ve kalemleri Türkçe para biçimiyle gösterir', () => {
    oturum(99, ['finans:oku']);
    ciz();
    expect(screen.getByText('Sac kesim hizmeti')).toBeInTheDocument();
    expect(screen.getAllByText('175,01 ₺').length).toBeGreaterThan(0);
    // Yalnız okuma yetkisi: aksiyon yok.
    expect(screen.queryByRole('button', { name: /Faturayı kes/ })).not.toBeInTheDocument();
  });

  it('onay yetkilisi başkasının faturasını kesebilir', () => {
    oturum(99, ['finans:oku', 'finans:onay']);
    ciz();
    expect(screen.getByRole('button', { name: /Faturayı kes/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: /Düzeltmeye iade et/ })).toBeEnabled();
  });

  it('hazırlayan kişi onay yetkisi olsa da kendi faturasını kesemez (görev ayrımı)', () => {
    oturum(11, ['finans:oku', 'finans:yaz', 'finans:onay']);
    ciz();
    expect(screen.getByRole('button', { name: /Faturayı kes/ })).toBeDisabled();
  });
});
