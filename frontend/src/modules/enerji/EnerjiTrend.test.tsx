import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';

import '@/i18n';

import { cizgiSecenek } from '@/components/grafik/grafikSecenek';

import { EnerjiTrend } from './EnerjiTrend';

// EGrafik canvas'ı test ortamında çalışmaz → basit yer tutucu ile değiştir.
vi.mock('@/components/grafik/EGrafik', () => ({
  EGrafik: () => <div data-testid="egrafik" />,
}));

// cizgiSecenek'i casus fonksiyonla değiştir (trend verisinin seçeneğe çevrildiğini doğrula).
vi.mock('@/components/grafik/grafikSecenek', () => ({
  cizgiSecenek: vi.fn(() => ({})),
}));

vi.mock('./hooks', () => ({
  useEnerjiTrend: () => ({
    data: [{ zaman: '2026-07-01T08:00:00Z', toplam: 120, adet: 3 }],
  }),
}));

describe('EnerjiTrend', () => {
  it('tür Select + aralık Segmented render eder ve trend verisini cizgiSecenek ile işler', () => {
    render(<EnerjiTrend />);
    // aralık Segmented etiketleri
    expect(screen.getByText('Saatlik')).toBeInTheDocument();
    expect(screen.getByText('Günlük')).toBeInTheDocument();
    // seçili tür (elektrik → Elektrik)
    expect(screen.getByText('Elektrik')).toBeInTheDocument();
    // CAGG trend noktası → { deger: toplam } eşlemesi
    expect(cizgiSecenek).toHaveBeenCalledWith([{ zaman: expect.any(String), deger: 120 }]);
  });
});
