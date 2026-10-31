import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { App as AntApp } from 'antd';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import type { Onizleme } from './hooks';
import { IceAktarma } from './IceAktarma';

const onizleMutate = vi.fn();
const uygulaMutate = vi.fn();
let onizlemeSonucu: Onizleme;

vi.mock('./hooks', () => ({
  useAktarimTurleri: () => ({
    isLoading: false,
    data: [
      {
        kod: 'makine',
        baslik: 'Makineler',
        aciklama: '',
        anahtar: ['kod'],
        yetkili: true,
        alanlar: [
          { ad: 'kod', zorunlu: true, aciklama: 'Benzersiz kod', ornek: 'CNC-01' },
          { ad: 'ad', zorunlu: true, aciklama: '', ornek: 'CNC Torna 1' },
        ],
      },
      {
        kod: 'personel',
        baslik: 'Personel',
        aciklama: '',
        anahtar: ['sicil_no'],
        yetkili: false,
        alanlar: [],
      },
    ],
  }),
  useOnizle: () => ({
    isPending: false,
    mutate: (arg: unknown, cb: { onSuccess: (o: Onizleme) => void }) => {
      onizleMutate(arg);
      cb.onSuccess(onizlemeSonucu);
    },
  }),
  useUygula: () => ({ isPending: false, mutate: uygulaMutate }),
  sablonIndir: vi.fn(),
}));

function bas() {
  render(
    <AntApp>
      <MemoryRouter>
        <IceAktarma />
      </MemoryRouter>
    </AntApp>,
  );
}

function dosyaBirak() {
  const girdi = document.querySelector('input[type="file"]') as HTMLInputElement;
  const dosya = new File(['kod;ad\nM1;Pres\n'], 'makineler.csv', { type: 'text/csv' });
  fireEvent.change(girdi, { target: { files: [dosya] } });
}

const temel: Onizleme = {
  tur: 'makine',
  toplam: 2,
  yeni: 1,
  guncelle: 1,
  ayni: 0,
  hatali: 0,
  eksik_kolonlar: [],
  bilinmeyen_kolonlar: [],
  satirlar: [
    { satir: 2, anahtar: 'M1', islem: 'yeni', hatalar: [], degisen: [] },
    { satir: 3, anahtar: 'M2', islem: 'guncelle', hatalar: [], degisen: ['durum'] },
  ],
};

describe('IceAktarma', () => {
  beforeEach(() => {
    onizleMutate.mockReset();
    uygulaMutate.mockReset();
  });

  it('yetkisiz tür kilitli, şablon kolonları görünür', () => {
    onizlemeSonucu = temel;
    bas();
    expect(screen.getByRole('button', { name: /Personel/ })).toBeDisabled();
    expect(screen.getByText('Benzersiz kod')).toBeInTheDocument();
  });

  it('hatasız önizleme uygulanabilir; uygula seçili türle çağrılır', async () => {
    onizlemeSonucu = temel;
    bas();
    dosyaBirak();
    await waitFor(() => expect(onizleMutate).toHaveBeenCalled());
    expect(onizleMutate).toHaveBeenCalledWith(expect.objectContaining({ tur: 'makine' }));
    expect(await screen.findByText(/Değişen: durum/)).toBeInTheDocument();
    const dugme = screen.getByRole('button', { name: /2 kaydı uygula/ });
    expect(dugme).toBeEnabled();
    fireEvent.click(dugme);
    expect(uygulaMutate).toHaveBeenCalledWith(
      expect.objectContaining({ tur: 'makine' }),
      expect.anything(),
    );
  });

  it('hatalı satır varsa uygula kapalı ve hata ayrıntısı listelenir', async () => {
    onizlemeSonucu = {
      ...temel,
      yeni: 1,
      guncelle: 0,
      hatali: 1,
      satirlar: [
        { satir: 2, anahtar: 'M1', islem: 'yeni', hatalar: [], degisen: [] },
        {
          satir: 3,
          anahtar: '',
          islem: 'hata',
          hatalar: [{ alan: 'durum', mesaj: 'Geçerli değerler: calisiyor, durdu' }],
          degisen: [],
        },
      ],
    };
    bas();
    dosyaBirak();
    expect(await screen.findByText(/Geçerli değerler/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /kaydı uygula/ })).toBeDisabled();
    // Hatalı satır varken süzgeç hatalılara geçer: yeni satır listede görünmez.
    expect(screen.queryByText('M1')).not.toBeInTheDocument();
  });
});
