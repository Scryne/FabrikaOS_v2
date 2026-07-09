import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';

import { MiniBar } from './MiniBar';

function dolu(node: HTMLElement): HTMLElement {
  return node.querySelector('.mini-bar-dolu') as HTMLElement;
}

describe('MiniBar', () => {
  it('deger/enBuyuk oranını scaleX olarak uygular', () => {
    const { container } = render(<MiniBar deger={50} enBuyuk={100} />);
    expect(dolu(container).style.transform).toBe('scaleX(0.5)');
  });

  it('değeri 0–1 aralığına sıkıştırır (taşma/negatif yok)', () => {
    const { container: askin } = render(<MiniBar deger={150} enBuyuk={100} />);
    expect(dolu(askin).style.transform).toBe('scaleX(1)');
    const { container: negatif } = render(<MiniBar deger={-5} enBuyuk={100} />);
    expect(dolu(negatif).style.transform).toBe('scaleX(0)');
  });
});
