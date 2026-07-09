import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import '@/i18n';

import { GorunumGecis } from './GorunumGecis';

describe('GorunumGecis', () => {
  it('Liste/Pano/Analiz seçeneklerini gösterir ve değişimi bildirir', async () => {
    const u = userEvent.setup();
    const degisti = vi.fn();
    render(<GorunumGecis deger="liste" degisti={degisti} />);

    expect(screen.getByText('Liste')).toBeInTheDocument();
    expect(screen.getByText('Pano')).toBeInTheDocument();
    expect(screen.getByText('Analiz')).toBeInTheDocument();

    await u.click(screen.getByText('Analiz'));
    expect(degisti).toHaveBeenCalledWith('analiz');
  });

  it('yalnız verilen seçenekleri gösterir', () => {
    render(<GorunumGecis deger="liste" degisti={vi.fn()} secenekler={['liste', 'pano']} />);
    expect(screen.getByText('Liste')).toBeInTheDocument();
    expect(screen.queryByText('Analiz')).not.toBeInTheDocument();
  });
});
