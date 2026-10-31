import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App } from 'antd';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';
import { useAuthStore } from '@/store/authStore';

import { OrgSemasi } from './OrgSemasi';
import { KontrolListesiSekmesi } from './PersonelOlgunluk';

vi.mock('./olgunlukHooks', () => ({
  useOrgSemasi: () => ({
    isPending: false,
    data: [
      {
        id: 1,
        ad_soyad: 'Ece Kaya',
        unvan: 'Fabrika müdürü',
        departman: 'Yönetim',
        yonetici_id: null,
        ast_sayisi: 1,
      },
      {
        id: 2,
        ad_soyad: 'Mert Ak',
        unvan: 'Üretim şefi',
        departman: 'Üretim',
        yonetici_id: 1,
        ast_sayisi: 1,
      },
      {
        id: 3,
        ad_soyad: 'Can Er',
        unvan: 'Operatör',
        departman: 'Üretim',
        yonetici_id: 2,
        ast_sayisi: 0,
      },
    ],
  }),
  useKontrolListeleri: () => ({
    isPending: false,
    data: [
      {
        id: 9,
        personel_id: 3,
        tur: 'cikis',
        durum: 'acik',
        tamamlanan: 0,
        toplam: 2,
        tamamlanma_tarihi: null,
        acik_zimmet: 2,
        maddeler: [
          { anahtar: 'zimmet_iade', ad: 'Zimmetler iade alındı', tamam: false },
          { anahtar: 'sgk_cikis', ad: 'SGK işten ayrılış bildirgesi verildi', tamam: false },
        ],
      },
    ],
  }),
  useKontrolListesiAc: () => ({ mutate: vi.fn(), isPending: false }),
  useMaddeIsaretle: () => ({ mutate: vi.fn(), isPending: false }),
}));

describe('S26-B İK ekranları', () => {
  it('org şeması yönetici zincirini iç içe ağaç olarak çizer', () => {
    render(
      <MemoryRouter>
        <OrgSemasi />
      </MemoryRouter>,
    );
    // Üç kişi de görünür (defaultExpandAll), kök sayısı 1.
    for (const ad of ['Ece Kaya', 'Mert Ak', 'Can Er'])
      expect(screen.getByText(ad)).toBeInTheDocument();
    // Girinti seviyesi = yönetici zincirindeki derinlik (antd ölçüm için gizli bir düğüm de basar).
    const derinlik = (ad: string) =>
      [...document.querySelectorAll('.ant-tree-treenode:not([aria-hidden="true"])')]
        .find((n) => n.textContent?.includes(ad))
        ?.querySelectorAll('.ant-tree-indent-unit').length;
    expect([derinlik('Ece Kaya'), derinlik('Mert Ak'), derinlik('Can Er')]).toEqual([0, 1, 2]);
  });

  it('çıkış listesi açık zimmeti uyarır; yazma izni yoksa maddeler kilitli', () => {
    useAuthStore.setState({ izinler: new Set(['ik:oku']) });
    render(
      <App>
        <KontrolListesiSekmesi personelId={3} />
      </App>,
    );
    expect(screen.getByText(/2 açık zimmet var/)).toBeInTheDocument();
    const kutular = screen.getAllByRole('checkbox');
    expect(kutular).toHaveLength(2);
    expect(kutular.every((k) => (k as HTMLInputElement).disabled)).toBe(true);
    expect(screen.queryByText('İşe giriş listesi aç')).not.toBeInTheDocument();
  });

  it('yazma izniyle eksik liste türü açılabilir, maddeler etkin', () => {
    useAuthStore.setState({ izinler: new Set(['ik:oku', 'ik:yaz']) });
    render(
      <App>
        <KontrolListesiSekmesi personelId={3} />
      </App>,
    );
    expect(screen.getByText('İşe giriş listesi aç')).toBeInTheDocument();
    expect(screen.queryByText('İşten çıkış listesi aç')).not.toBeInTheDocument(); // zaten var
    expect(screen.getAllByRole('checkbox').every((k) => !(k as HTMLInputElement).disabled)).toBe(
      true,
    );
  });
});
