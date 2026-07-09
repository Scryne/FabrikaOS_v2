import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import '@/i18n';

import { RiskMatrisi } from './RiskMatrisi';

describe('RiskMatrisi', () => {
  it('hücre sayacını gösterir ve tıklamada olasılık/şiddeti bildirir', async () => {
    const u = userEvent.setup();
    const onHucre = vi.fn();
    // Yalnız en yüksek risk hücresinde (5×5) 3 kayıt.
    const sayac = (o: number, s: number) => (o === 5 && s === 5 ? 3 : 0);
    render(<RiskMatrisi sayac={sayac} renk={() => '#ef4444'} onHucre={onHucre} />);

    // En yüksek risk hücresi (5×5) 3 kaydı gösterir; eksen etiketleriyle karışmasın diye
    // hücreyi benzersiz aria-label'ından buluruz.
    const hucre = screen.getByLabelText(/Olasılık 5, Şiddet 5: 3/);
    expect(hucre).toHaveTextContent('3');

    await u.click(hucre);
    expect(onHucre).toHaveBeenCalledWith(5, 5);
  });
});
