import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { OzetSerit } from './OzetSerit';

describe('OzetSerit', () => {
  it('metrikleri başlık + değerle gösterir', () => {
    render(
      <OzetSerit
        metrikler={[
          { anahtar: 'a', baslik: 'Açık iş emri', deger: '12' },
          { anahtar: 'b', baslik: 'Kritik stok', deger: '3' },
        ]}
      />,
    );
    expect(screen.getByText('Açık iş emri')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('Kritik stok')).toBeInTheDocument();
  });

  it('yukleniyor iken metrik metni göstermez (skeleton)', () => {
    render(<OzetSerit metrikler={[]} yukleniyor />);
    expect(screen.queryByText('Açık iş emri')).not.toBeInTheDocument();
  });
});
