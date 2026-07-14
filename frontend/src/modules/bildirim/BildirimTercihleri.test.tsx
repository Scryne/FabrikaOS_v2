import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { BildirimTercihleri } from './BildirimTercihleri';

const guncelleMutate = vi.fn();

vi.mock('./hooks', () => ({
  useBildirimTercihleri: () => ({
    isLoading: false,
    data: [
      { olay_turu: 'stok.kritik', uygulama_ici: true, eposta: false },
      { olay_turu: 'rapor.hazir', uygulama_ici: true, eposta: true },
    ],
  }),
  useTercihGuncelle: () => ({ mutate: guncelleMutate }),
}));

describe('BildirimTercihleri', () => {
  it('katalog satırlarını gösterir; anahtar değişimi tek satır upsert eder', () => {
    render(
      <MemoryRouter>
        <BildirimTercihleri />
      </MemoryRouter>,
    );
    expect(screen.getByText('stok.kritik')).toBeInTheDocument();
    expect(screen.getByText('rapor.hazir')).toBeInTheDocument();

    // stok.kritik uygulama-içi anahtarını kapat → mutate güncel satırla çağrılır.
    fireEvent.click(screen.getByRole('switch', { name: 'stok.kritik Uygulama içi' }));
    expect(guncelleMutate).toHaveBeenCalledWith([
      { olay_turu: 'stok.kritik', uygulama_ici: false, eposta: false },
    ]);
  });
});
