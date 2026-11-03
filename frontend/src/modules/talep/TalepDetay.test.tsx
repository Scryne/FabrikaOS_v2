import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';
import { useAuthStore } from '@/store/authStore';

import { TalepDetay } from './TalepDetay';

// Okunur adlar mevcut izin kapılarından gelir: kullanıcı listesi ``kullanici:oku``, firma
// ``crm:oku``. Kapı kapalıyken sorgu hiç çalışmamalı (RBAC gevşemez), ekran kayıt numarasına düşer.
const kullaniciCagrisi = vi.fn();
const firmaCagrisi = vi.fn();

vi.mock('@/modules/isemri/hooks', () => ({
  useKullaniciSecenekleri: (etkin: boolean) => {
    kullaniciCagrisi(etkin);
    return {
      data: etkin
        ? [{ id: 3, ad_soyad: 'Deniz Aydın', eposta: 'crm@alfa.test', aktif: true }]
        : undefined,
      isFetching: false,
    };
  },
}));
vi.mock('@/modules/crm/hooks', () => ({
  useFirma: (id: number) => {
    firmaCagrisi(id);
    return { data: id > 0 ? { id, ad: 'Anadolu Metal A.Ş.' } : undefined, isFetching: false };
  },
}));
vi.mock('./hooks', () => {
  const mut = () => ({ mutate: vi.fn(), mutateAsync: vi.fn(), isPending: false });
  return {
    useTalep: () => ({
      data: {
        id: 11,
        kod: 'TLP-2026-000011',
        baslik: 'Teslim tarihi sorusu',
        aciklama: '',
        tur: 'bilgi',
        oncelik: 'orta',
        durum: 'acik',
        firma_id: 4,
        atanan_kullanici_id: 3,
      },
    }),
    useTalepDurum: mut,
    useTalepGuncelle: mut,
  };
});

function ciz(izinler: string[]) {
  useAuthStore.setState({ izinler: new Set(izinler) });
  render(
    <MemoryRouter>
      <TalepDetay id={11} kapat={() => {}} />
    </MemoryRouter>,
  );
}

describe('TalepDetay', () => {
  beforeEach(() => {
    kullaniciCagrisi.mockClear();
    firmaCagrisi.mockClear();
  });

  it('atanan kişiyi ve firmayı adıyla gösterir', () => {
    ciz(['talep:oku', 'kullanici:oku', 'crm:oku']);
    expect(screen.getByText('Deniz Aydın')).toBeInTheDocument();
    expect(screen.getByText('Anadolu Metal A.Ş.')).toBeInTheDocument();
    expect(screen.queryByText(/#3\b/)).not.toBeInTheDocument();
    expect(screen.queryByText(/#4\b/)).not.toBeInTheDocument();
  });

  it('izin yokken adları çekmez (RBAC), kayıt numarasına düşer', () => {
    ciz(['talep:oku']);
    expect(kullaniciCagrisi).not.toHaveBeenCalledWith(true);
    expect(firmaCagrisi).not.toHaveBeenCalledWith(4);
    expect(screen.getByText('#3')).toBeInTheDocument();
    expect(screen.getByText('#4')).toBeInTheDocument();
  });

  it('kullanici:oku ile atama kişi seçicisiyle, değilse numarayla yapılır', () => {
    ciz(['talep:oku', 'talep:yaz', 'kullanici:oku']);
    expect(screen.getByRole('combobox', { name: 'Atanan' })).toBeInTheDocument();
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
  });

  it('kullanici:oku yokken atama özelliği numara girişiyle korunur', () => {
    ciz(['talep:oku', 'talep:yaz']);
    expect(screen.getByRole('spinbutton')).toBeInTheDocument();
  });
});
