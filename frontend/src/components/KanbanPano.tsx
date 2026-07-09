/**
 * Genelleştirilmiş kanban panosu — durum sütunları + kartlar. ``IsEmriKanban``'dan soyutlandı:
 * kolonlar (durum + renk + başlık), öğeleri kolon anahtarına göre istemcide gruplar, her kartı
 * ``kartCiz`` ile çizer. Kolon başlığı durum noktası + sayaç taşır. Yatay kaydırmalı (çok kolon).
 */

import type { Key, ReactNode } from 'react';

export type KanbanKolon = {
  anahtar: string;
  baslik: ReactNode;
  /** Kolon başlığı durum noktası rengi (nokta + başlık birlikte anlam taşır). */
  renk: string;
};

export function KanbanPano<T>({
  kolonlar,
  ogeler,
  kolonAnahtar,
  kartCiz,
  kartAnahtar,
  bosMetin,
}: {
  kolonlar: KanbanKolon[];
  ogeler: T[];
  /** Öğenin ait olduğu kolon anahtarı. */
  kolonAnahtar: (o: T) => string;
  kartCiz: (o: T) => ReactNode;
  kartAnahtar: (o: T) => Key;
  /** Boş kolon metni. */
  bosMetin?: ReactNode;
}) {
  const gruplar = new Map<string, T[]>(kolonlar.map((k) => [k.anahtar, []]));
  for (const o of ogeler) {
    gruplar.get(kolonAnahtar(o))?.push(o);
  }

  return (
    <div className="board-serit">
      {kolonlar.map((k) => {
        const grup = gruplar.get(k.anahtar) ?? [];
        return (
          <div key={k.anahtar} className="board-kolon">
            <div className="board-kolon-baslik">
              <span
                style={{
                  fontWeight: 600,
                  color: 'var(--metin)',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                }}
              >
                <span className="durum-nokta" aria-hidden="true" style={{ background: k.renk }} />
                {k.baslik}
              </span>
              <span className="sayisal board-sayac">{grup.length}</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {grup.map((o) => (
                <div key={kartAnahtar(o)}>{kartCiz(o)}</div>
              ))}
              {grup.length === 0 && (
                <div style={{ color: 'var(--metin-soluk)', fontSize: 12, padding: '8px 4px' }}>
                  {bosMetin}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
