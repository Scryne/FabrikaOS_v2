import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import '@/i18n';

import { DurumPim, pimUret } from './DurumPim';

describe('DurumPim', () => {
  it('etiketi gösterir (nokta + metin birlikte anlam taşır)', () => {
    const { container } = render(<DurumPim renk="#22c55e" etiket="Çalışıyor" />);
    expect(screen.getByText('Çalışıyor')).toBeInTheDocument();
    expect(container.querySelector('.pim-nokta')).not.toBeNull();
  });
});

describe('pimUret', () => {
  it('durum→renk haritası + i18n önekinden pim bileşeni üretir', () => {
    const Pim = pimUret({ acik: '#8c8c92' }, 'isemri.durum_');
    render(<Pim durum="acik" />);
    expect(screen.getByText('Açık')).toBeInTheDocument();
  });
});
