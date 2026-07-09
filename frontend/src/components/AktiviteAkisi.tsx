/**
 * Aktivite akışı / zaman çizelgesi — renkli nokta + başlık + (opsiyonel) açıklama + zaman.
 * Panolarda son olaylar, detay ekranlarında yaşam döngüsü aşamaları için. AntD ``Timeline``.
 */

import type { ReactNode } from 'react';
import { Timeline } from 'antd';

import { BosDurum } from '@/components/BosDurum';
import { RENKLER } from '@/tema/tema';

export type AktiviteOge = {
  anahtar: string;
  /** Nokta rengi (hex önerilir; ör. RENKLER.mavi). */
  renk?: string;
  baslik: ReactNode;
  aciklama?: ReactNode;
  zaman?: ReactNode;
};

export function AktiviteAkisi({ ogeler, bos }: { ogeler: AktiviteOge[]; bos?: ReactNode }) {
  if (ogeler.length === 0) return <>{bos ?? <BosDurum baslik="—" />}</>;
  return (
    <Timeline
      items={ogeler.map((o) => ({
        key: o.anahtar,
        color: o.renk ?? RENKLER.mavi,
        children: (
          <div>
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                gap: 12,
                alignItems: 'baseline',
              }}
            >
              <span style={{ color: 'var(--metin)', fontWeight: 500 }}>{o.baslik}</span>
              {o.zaman && (
                <span
                  className="sayisal"
                  style={{ color: 'var(--metin-soluk)', fontSize: 12, whiteSpace: 'nowrap' }}
                >
                  {o.zaman}
                </span>
              )}
            </div>
            {o.aciklama && (
              <div style={{ color: 'var(--metin-soluk)', fontSize: 13, marginTop: 2 }}>
                {o.aciklama}
              </div>
            )}
          </div>
        ),
      }))}
    />
  );
}
