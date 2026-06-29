/** KPI metrik kartı — büyük mono sayı + opsiyonel dönemsel delta veya alt etiket. */

import type { ReactNode } from 'react';
import { ArrowDownOutlined, ArrowUpOutlined } from '@ant-design/icons';
import { Card } from 'antd';

export function KpiKart({
  baslik,
  deger,
  birim,
  ikon,
  deltaMetin,
  yon,
  olumlu,
  altMetin,
}: {
  baslik: string;
  deger: string;
  birim?: string;
  ikon?: ReactNode;
  /** Verilirse delta satırı (ok + renkli yüzde) gösterilir; yoksa yalnız alt metin. */
  deltaMetin?: string;
  yon?: 'yukari' | 'asagi';
  olumlu?: boolean;
  altMetin?: string;
}) {
  const renk = olumlu ? 'var(--basari)' : 'var(--hata)';
  return (
    <Card size="small" styles={{ body: { padding: 18 } }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 8,
        }}
      >
        <span style={{ color: 'var(--metin-soluk)', fontSize: 13, fontWeight: 500 }}>{baslik}</span>
        {ikon && <span style={{ color: 'var(--metin-soluk)' }}>{ikon}</span>}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 10 }}>
        <span
          className="sayisal"
          style={{ fontSize: 27, fontWeight: 700, color: 'var(--metin)', letterSpacing: '-0.02em' }}
        >
          {deger}
        </span>
        {birim && <span style={{ color: 'var(--metin-soluk)', fontSize: 13 }}>{birim}</span>}
      </div>
      {(deltaMetin || altMetin) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 7,
            marginTop: 10,
            fontSize: 12.5,
          }}
        >
          {deltaMetin && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 3,
                color: renk,
                fontWeight: 600,
              }}
            >
              {yon === 'asagi' ? <ArrowDownOutlined /> : <ArrowUpOutlined />}
              {deltaMetin}
            </span>
          )}
          {altMetin && <span style={{ color: 'var(--metin-soluk)' }}>{altMetin}</span>}
        </div>
      )}
    </Card>
  );
}
