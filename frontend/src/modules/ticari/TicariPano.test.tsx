import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import { App as AntApp } from 'antd';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TicariPano } from './TicariPano';

vi.mock('@/api/client', async () => {
  const gercek = await vi.importActual<typeof import('@/api/client')>('@/api/client');
  return {
    ...gercek,
    istek: vi.fn().mockResolvedValue({
      sayaclar: {
        firma_sayisi: 7,
        aktif_firma: 5,
        aktif_sozlesme: 3,
        yaklasan_sozlesme: 2,
        acik_talep: 4,
        yayinli_duyuru: 1,
      },
      yaklasan_sozlesmeler: [
        {
          id: 1,
          kod: 'SZ-2026-000001',
          firma_id: 1,
          baslik: 'Bakım',
          bitis_tarihi: '2026-07-20',
          kalan_gun: 16,
          tutar: 1000,
          para_birimi: 'TRY',
        },
      ],
      son_duyurular: [
        {
          id: 1,
          kod: 'DUY-2026-000001',
          baslik: 'Duyuru',
          onem: 'uyari',
          yayin_tarihi: '2026-07-04T10:00:00Z',
        },
      ],
    }),
  };
});

function sar(ui: React.ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <AntApp>{ui}</AntApp>
    </QueryClientProvider>,
  );
}

describe('TicariPano', () => {
  beforeEach(() => vi.clearAllMocks());

  it('sayaçları ve yaklaşan sözleşmeyi gösterir', async () => {
    sar(<TicariPano />);
    await waitFor(() => expect(screen.getByText('SZ-2026-000001')).toBeInTheDocument());
    expect(screen.getByText('7')).toBeInTheDocument(); // firma sayısı
    expect(screen.getByText('Duyuru')).toBeInTheDocument();
  });
});
