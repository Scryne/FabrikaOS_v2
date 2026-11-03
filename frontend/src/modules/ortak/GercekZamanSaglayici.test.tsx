import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { gercekZamanBaglan } from '@/api/gercekzaman';
import { useAuthStore } from '@/store/authStore';

import { GercekZamanSaglayici } from './GercekZamanSaglayici';
import { useGercekZaman } from './gercekZamanBaglam';

const kapat = vi.fn();
vi.mock('@/api/gercekzaman', () => ({ gercekZamanBaglan: vi.fn(() => ({ kapat })) }));
vi.mock('@/api/tenant', () => ({ cozumleTenant: () => 'alfa' }));

function Gosterge() {
  const { bagli } = useGercekZaman();
  return <span>{bagli ? 'canli' : 'kopuk'}</span>;
}

function kur() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <GercekZamanSaglayici>
        <Gosterge />
      </GercekZamanSaglayici>
    </QueryClientProvider>,
  );
}

function sonOnDurum(): (bagli: boolean) => void {
  const cagri = vi.mocked(gercekZamanBaglan).mock.calls.at(-1);
  if (!cagri?.[0].onDurum) throw new Error('bağlantı kurulmadı');
  return cagri[0].onDurum;
}

describe('GercekZamanSaglayici', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({ girisYapildi: false, access: null });
  });

  it('oturum yokken soket açılmaz, gösterge kopuk', () => {
    kur();
    expect(gercekZamanBaglan).not.toHaveBeenCalled();
    expect(screen.getByText('kopuk')).toBeInTheDocument();
  });

  it('önizlemede soket açılmadan canlı sayılır', () => {
    useAuthStore.setState({ girisYapildi: true, access: 'onizleme' });
    kur();
    expect(gercekZamanBaglan).not.toHaveBeenCalled();
    expect(screen.getByText('canli')).toBeInTheDocument();
  });

  it('bağlantı durumunu soketten alır; token yenilemesi soketi yeniden açtırmaz', () => {
    useAuthStore.setState({ girisYapildi: true, access: 'jeton-1' });
    kur();
    expect(gercekZamanBaglan).toHaveBeenCalledTimes(1);
    expect(screen.getByText('kopuk')).toBeInTheDocument();

    act(() => sonOnDurum()(true));
    expect(screen.getByText('canli')).toBeInTheDocument();

    act(() => useAuthStore.setState({ access: 'jeton-2' }));
    expect(gercekZamanBaglan).toHaveBeenCalledTimes(1);
    expect(screen.getByText('canli')).toBeInTheDocument();
  });

  it('çıkışta soket kapanır ve gösterge kopuk olur', () => {
    useAuthStore.setState({ girisYapildi: true, access: 'jeton-1' });
    kur();
    act(() => sonOnDurum()(true));

    act(() => useAuthStore.setState({ girisYapildi: false, access: null }));
    expect(kapat).toHaveBeenCalledTimes(1);
    expect(screen.getByText('kopuk')).toBeInTheDocument();
  });
});
