import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';
import { girisYap, ikiAsamaDogrula, ssoAcikMi, ssoBaslat } from '@/api/kimlik';

import { GirisSayfasi } from './GirisSayfasi';

vi.mock('@/api/kimlik', () => ({
  girisYap: vi.fn(),
  ikiAsamaDogrula: vi.fn(),
  ssoAcikMi: vi.fn(),
  ssoBaslat: vi.fn(),
  // Zorunlu-2FA dalında kurulum sihirbazı mount olur; sır/QR çağrısı sahtelenir.
  ikiAsamaKur: vi.fn().mockResolvedValue({ sir: 'JBSWY3DPEHPK3PXP', otpauth_uri: 'otpauth://x' }),
  ikiAsamaEtkinlestir: vi.fn().mockResolvedValue(['AAAA-BBBB']),
}));

function ekranaBas() {
  render(
    <MemoryRouter>
      <GirisSayfasi />
    </MemoryRouter>,
  );
}

async function parolaDoldur(u: ReturnType<typeof userEvent.setup>) {
  await u.type(screen.getByLabelText(/firma kodu/i), 'alfa');
  await u.type(screen.getByLabelText(/e-posta/i), 'admin@alfa.test');
  await u.type(screen.getByLabelText(/^parola/i), 'Parola123!');
  await u.click(screen.getByRole('button', { name: /giriş yap/i }));
}

describe('GirisSayfasi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(girisYap).mockResolvedValue({ durum: 'tamam' });
    vi.mocked(ikiAsamaDogrula).mockResolvedValue({ durum: 'tamam' });
    vi.mocked(ssoAcikMi).mockResolvedValue(false);
    vi.mocked(ssoBaslat).mockResolvedValue('https://idp.test/auth?x=1');
  });

  it('subdomain yokken firma kodu alanı görünür ve giriş çağrılır', async () => {
    // jsdom host = localhost → subdomain yok → fallback firma kodu alanı.
    const u = userEvent.setup();
    ekranaBas();

    expect(screen.getByLabelText(/firma kodu/i)).toBeInTheDocument();
    await parolaDoldur(u);

    await waitFor(() =>
      expect(girisYap).toHaveBeenCalledWith('alfa', 'admin@alfa.test', 'Parola123!'),
    );
  });

  it('2FA gerekiyorsa kod adımına geçer ve kodu doğrular', async () => {
    vi.mocked(girisYap).mockResolvedValue({ durum: '2fa', geciciToken: 'gecici-abc' });
    const u = userEvent.setup();
    ekranaBas();

    await parolaDoldur(u);

    // Parola formu yerini ikinci adıma bırakır (yarım oturum ekranda kalmaz).
    const kodAlani = await screen.findByLabelText(/doğrulama kodu/i);
    expect(screen.queryByLabelText(/^parola/i)).not.toBeInTheDocument();

    await u.type(kodAlani, '123456');
    await u.click(screen.getByRole('button', { name: /^doğrula$/i }));

    await waitFor(() => expect(ikiAsamaDogrula).toHaveBeenCalledWith('gecici-abc', '123456'));
  });

  it('zorunlu 2FA kurulumunda kurulum sihirbazına yönlendirir', async () => {
    vi.mocked(girisYap).mockResolvedValue({ durum: '2fa-kurulum', geciciToken: 'kurulum-abc' });
    const u = userEvent.setup();
    ekranaBas();

    await parolaDoldur(u);

    // Not: regex Türkçe "İ" ile başlatılmaz — JS büyük/küçük katlaması U+0130'u 'i' ile eşlemez.
    expect(await screen.findByText(/aşamalı doğrulama zorunlu/i)).toBeInTheDocument();
  });

  it('SSO kapalıyken düğme gösterilmez', async () => {
    const u = userEvent.setup();
    ekranaBas();

    await u.type(screen.getByLabelText(/firma kodu/i), 'alfa');
    await waitFor(() => expect(ssoAcikMi).toHaveBeenCalled());

    expect(screen.queryByRole('button', { name: /kurumsal hesapla giriş/i })).toBeNull();
  });

  it('SSO açıkken düğme görünür ve IdP adresi istenir', async () => {
    vi.mocked(ssoAcikMi).mockResolvedValue(true);
    const u = userEvent.setup();
    ekranaBas();

    await u.type(screen.getByLabelText(/firma kodu/i), 'alfa');
    const ssoDugmesi = await screen.findByRole('button', { name: /kurumsal hesapla giriş/i });
    await u.click(ssoDugmesi);

    await waitFor(() => expect(ssoBaslat).toHaveBeenCalledWith('alfa'));
  });
});
