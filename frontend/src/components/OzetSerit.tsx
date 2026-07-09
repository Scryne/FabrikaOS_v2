/**
 * Özet şeridi — modül üstü KPI/özet kartları (3-4 metrik). Her metrik ``KpiKart`` olur;
 * ikon plakası modül hat rengini (``renk``) taşır. ``yukleniyor`` iken sakin skeleton ızgarası.
 * Veri ``use<Modul>Ozet()`` hook'undan gelen küçük ``/ozet`` yanıtından beslenir.
 */

import type { ReactNode } from 'react';
import { Card, Skeleton } from 'antd';

import { KpiKart } from '@/components/KpiKart';

export type OzetMetrik = {
  /** React key (ör. 'oee'). */
  anahtar: string;
  baslik: string;
  deger: string;
  birim?: string;
  ikon?: ReactNode;
  seri?: number[];
  deltaMetin?: string;
  yon?: 'yukari' | 'asagi';
  olumlu?: boolean;
  altMetin?: string;
};

export function OzetSerit({
  metrikler,
  renk,
  yukleniyor,
}: {
  metrikler: OzetMetrik[];
  /** Modül hat rengi (KPI ikon plakalarına uygulanır). */
  renk?: string;
  yukleniyor?: boolean;
}) {
  if (yukleniyor) {
    return (
      <div className="ozet-serit">
        {[0, 1, 2, 3].map((i) => (
          <Card key={i} size="small" styles={{ body: { padding: 18 } }}>
            <Skeleton active paragraph={{ rows: 1 }} title={{ width: '55%' }} />
          </Card>
        ))}
      </div>
    );
  }
  return (
    <div className="ozet-serit">
      {metrikler.map(({ anahtar, ...m }) => (
        <KpiKart key={anahtar} renk={renk} {...m} />
      ))}
    </div>
  );
}
