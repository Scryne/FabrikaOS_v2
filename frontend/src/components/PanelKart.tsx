/**
 * Enstrüman-panel kartı — üst iç ışık çizgisi + başlıkta hat renkli ince aksan çubuğu + sağ
 * "extra" alanı. Panolar, analiz ve detay bölmeleri bu kartla kurulur (AntD ``Card`` üstünde
 * ince bir "deri"). ``renk`` verilmezse aksan vurgu mavisine düşer.
 */

import type { CSSProperties, ReactNode } from 'react';
import { Card } from 'antd';

export function PanelKart({
  baslik,
  ikon,
  sag,
  renk,
  children,
  govdeDolgu = 20,
  sinif,
}: {
  baslik?: ReactNode;
  ikon?: ReactNode;
  /** Başlık sağındaki ek alan (AntD extra). */
  sag?: ReactNode;
  /** Hat aksanı rengi (hex/var); verilmezse mavi. */
  renk?: string;
  children: ReactNode;
  govdeDolgu?: number | string;
  sinif?: string;
}) {
  return (
    <Card
      className={sinif ? `panel-kart ${sinif}` : 'panel-kart'}
      style={{ '--hat': renk ?? 'var(--mavi)' } as CSSProperties}
      title={
        baslik ? (
          <span className="panel-kart-baslik">
            <i className="panel-kart-aksan" aria-hidden="true" />
            {ikon}
            {baslik}
          </span>
        ) : undefined
      }
      extra={sag}
      styles={{ body: { padding: govdeDolgu } }}
    >
      {children}
    </Card>
  );
}
