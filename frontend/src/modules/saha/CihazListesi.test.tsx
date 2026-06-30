import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

import '@/i18n';

import { CihazListesi } from './CihazListesi';

vi.mock('./hooks', () => ({
  useCihazlar: () => ({
    data: {
      veri: [
        {
          id: 1,
          kod: 'GW-1',
          ad: 'Gateway 1',
          protokol: 'simulasyon',
          aktif: true,
          son_gorulme: null,
        },
      ],
      meta: { sayfa: 1, adet: 20, toplam: 1 },
    },
    isPending: false,
    isError: false,
  }),
}));

describe('CihazListesi', () => {
  it('cihazları sunucu-taraflı tabloda listeler', () => {
    render(
      <MemoryRouter>
        <CihazListesi />
      </MemoryRouter>,
    );
    expect(screen.getByText('GW-1')).toBeInTheDocument();
    expect(screen.getByText('Gateway 1')).toBeInTheDocument();
  });
});
