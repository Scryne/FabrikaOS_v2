import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import '@/i18n';

import { useAuthStore } from '@/store/authStore';

import { KullaniciFormu } from './KullaniciFormu';

vi.mock('./hooks', () => ({
  useRoller: () => ({ data: [{ id: 1, ad: 'admin', aciklama: '', izinler: [] }] }),
  useFirmaSecenekleri: () => ({ data: [{ id: 5, ad: 'Acme A.Ş.' }] }),
  useKullaniciOlustur: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useKullaniciGuncelle: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

vi.mock('@/modules/abonelik/hooks', () => ({ useModulAcik: () => () => true }));

const DUZENLENEN = {
  id: 2,
  eposta: 'izleyici@alfa.test',
  ad_soyad: 'Salt Okur',
  aktif: true,
  roller: ['admin'],
  firma_id: null,
};

function oturum(izinler: string[]) {
  useAuthStore.getState().ayarlaOturum('access', {
    id: 1,
    eposta: 'admin@alfa.test',
    ad_soyad: 'Yönetici',
    roller: ['admin'],
    izinler,
  });
}

describe('KullaniciFormu', () => {
  beforeEach(() => useAuthStore.getState().temizle());

  it('oluşturma modu: e-posta + parola alanları var, aktiflik anahtarı yok', () => {
    oturum(['kullanici:yaz', 'rol:oku']);
    render(<KullaniciFormu acik kapat={() => {}} />);
    expect(screen.getByText('Yeni kullanıcı')).toBeInTheDocument();
    expect(screen.getByLabelText('Parola')).toBeInTheDocument();
    expect(screen.queryByRole('switch')).not.toBeInTheDocument();
  });

  it('düzenleme modu: e-posta kilitli, parola yok, aktiflik anahtarı var', () => {
    oturum(['kullanici:yaz', 'rol:oku']);
    render(<KullaniciFormu acik kapat={() => {}} duzenlenen={DUZENLENEN} />);
    expect(screen.getByText('Kullanıcıyı düzenle')).toBeInTheDocument();
    // requiredMark="optional": zorunlu olmayan etiketlere "(optional)" eklenir → regex.
    expect(screen.getByLabelText(/E-posta/)).toBeDisabled();
    expect(screen.queryByLabelText(/Parola/)).not.toBeInTheDocument();
    expect(screen.getByRole('switch')).toBeEnabled();
  });

  it('kendi hesabında aktiflik anahtarı kilitlidir (backend 422 korumasının aynası)', () => {
    oturum(['kullanici:yaz', 'rol:oku']);
    render(<KullaniciFormu acik kapat={() => {}} duzenlenen={{ ...DUZENLENEN, id: 1 }} />);
    expect(screen.getByRole('switch')).toBeDisabled();
  });

  it('crm:oku ile firma seçimi görünür (dış portal bağlantısı)', () => {
    oturum(['kullanici:yaz', 'rol:oku', 'crm:oku']);
    render(<KullaniciFormu acik kapat={() => {}} duzenlenen={DUZENLENEN} />);
    expect(screen.getByText('Firma (dış portal)')).toBeInTheDocument();
  });

  it('crm:oku olmadan firma alanı gizlidir', () => {
    oturum(['kullanici:yaz', 'rol:oku']);
    render(<KullaniciFormu acik kapat={() => {}} duzenlenen={DUZENLENEN} />);
    expect(screen.queryByText('Firma (dış portal)')).not.toBeInTheDocument();
  });
});
