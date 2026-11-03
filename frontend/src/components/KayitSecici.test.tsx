import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { KayitSecici } from './KayitSecici';

describe('KayitSecici', () => {
  it('izin varsa kaydı adıyla gösterir', () => {
    render(<KayitSecici izinli secenekler={[{ value: 6, label: 'Selin Kaya' }]} value={6} />);
    expect(screen.getByText('Selin Kaya')).toBeInTheDocument();
    expect(screen.queryByRole('spinbutton')).not.toBeInTheDocument();
  });

  it('izin yoksa form numarayla çalışmaya devam eder', () => {
    render(<KayitSecici izinli={false} secenekler={[]} value={6} />);
    expect(screen.getByRole('spinbutton')).toHaveValue('6');
  });
});
