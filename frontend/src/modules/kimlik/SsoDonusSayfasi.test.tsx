import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

import '@/i18n';
import { ssoTamamla } from '@/api/kimlik';

import { SsoDonusSayfasi } from './SsoDonusSayfasi';

vi.mock('@/api/kimlik', () => ({ ssoTamamla: vi.fn() }));

function ekranaBas(adres: string) {
  render(
    <MemoryRouter initialEntries={[adres]}>
      <Routes>
        <Route path="/sso/donus" element={<SsoDonusSayfasi />} />
        <Route path="/pano" element={<div>pano-ekrani</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe('SsoDonusSayfasi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(ssoTamamla).mockResolvedValue({ durum: 'tamam' });
  });

  it('IdP hatası açıklamasıyla gösterilir, sunucuya gidilmez', () => {
    ekranaBas('/sso/donus?error=access_denied&error_description=Reddedildi');
    expect(screen.getByText('Reddedildi')).toBeInTheDocument();
    expect(ssoTamamla).not.toHaveBeenCalled();
  });

  it('kod ya da state eksikse sunucuya gidilmez', () => {
    ekranaBas('/sso/donus?code=abc');
    expect(screen.getByText('Dönüş adresinde kod veya state bilgisi yok')).toBeInTheDocument();
    expect(ssoTamamla).not.toHaveBeenCalled();
  });

  it('kod ve state ile bir kez tamamlanır ve panoya gider', async () => {
    ekranaBas('/sso/donus?code=abc&state=xyz');
    expect(await screen.findByText('pano-ekrani')).toBeInTheDocument();
    expect(ssoTamamla).toHaveBeenCalledTimes(1);
    expect(ssoTamamla).toHaveBeenCalledWith('abc', 'xyz');
  });

  it('sunucu hatası gösterilir', async () => {
    vi.mocked(ssoTamamla).mockRejectedValue(new Error('x'));
    ekranaBas('/sso/donus?code=abc&state=xyz');
    await waitFor(() => expect(screen.getByText('SSO girişi tamamlanamadı')).toBeInTheDocument());
  });
});
