import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import { KanbanPano } from './KanbanPano';

type Oge = { id: number; durum: string; ad: string };

const KOLONLAR = [
  { anahtar: 'acik', baslik: 'Açık', renk: '#8c8c92' },
  { anahtar: 'kapandi', baslik: 'Kapandı', renk: '#22c55e' },
];

describe('KanbanPano', () => {
  it('öğeleri kolon anahtarına göre gruplar ve sayaçları gösterir', () => {
    render(
      <KanbanPano<Oge>
        kolonlar={KOLONLAR}
        ogeler={[
          { id: 1, durum: 'acik', ad: 'İş A' },
          { id: 2, durum: 'acik', ad: 'İş B' },
          { id: 3, durum: 'kapandi', ad: 'İş C' },
        ]}
        kolonAnahtar={(o) => o.durum}
        kartAnahtar={(o) => o.id}
        kartCiz={(o) => <span>{o.ad}</span>}
        bosMetin="Boş"
      />,
    );
    expect(screen.getByText('İş A')).toBeInTheDocument();
    expect(screen.getByText('İş C')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument(); // açık kolonu
    expect(screen.getByText('1')).toBeInTheDocument(); // kapandı kolonu
  });

  it('boş kolonda bos metnini gösterir', () => {
    render(
      <KanbanPano<Oge>
        kolonlar={KOLONLAR}
        ogeler={[{ id: 1, durum: 'acik', ad: 'İş A' }]}
        kolonAnahtar={(o) => o.durum}
        kartAnahtar={(o) => o.id}
        kartCiz={(o) => <span>{o.ad}</span>}
        bosMetin="Boş kolon"
      />,
    );
    expect(screen.getByText('Boş kolon')).toBeInTheDocument();
  });
});
