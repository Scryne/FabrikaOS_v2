/**
 * KPI metrik kartı — büyük mono sayı + hat renkli ikon plakası + opsiyonel dönemsel delta
 * veya alt etiket. ``renk`` modül hat renginden gelir (tema/modulKimlik.BOLUM_RENGI).
 */

import type { CSSProperties, ReactNode } from 'react';
import { ArrowDownOutlined, ArrowUpOutlined } from '@ant-design/icons';
import { Card } from 'antd';

import { MiniTrend } from '@/components/MiniTrend';

export function KpiKart({
  baslik,
  deger,
  birim,
  ikon,
  renk,
  deltaMetin,
  yon,
  olumlu,
  altMetin,
  seri,
}: {
  baslik: string;
  deger: string;
  birim?: string;
  ikon?: ReactNode;
  /** İkon plakası hat rengi (hex/var); verilmezse vurgu mavisi. */
  renk?: string;
  /** Verilirse delta satırı (ok + renkli yüzde) gösterilir; yoksa yalnız alt metin. */
  deltaMetin?: string;
  yon?: 'yukari' | 'asagi';
  olumlu?: boolean;
  altMetin?: string;
  /** Verilirse kartın altında satır-içi sparkline çizilir (modül hat renginde). */
  seri?: number[];
}) {
  const deltaRenk = olumlu ? 'var(--basari)' : 'var(--hata)';
  return (
    <Card size="small" styles={{ body: { padding: 18 } }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          gap: 8,
        }}
      >
        <span style={{ color: 'var(--metin-soluk)', fontSize: 13, fontWeight: 500, marginTop: 5 }}>
          {baslik}
        </span>
        {ikon && (
          <span
            className="ikon-plaka kucuk"
            aria-hidden="true"
            style={{ '--plaka-renk': renk ?? 'var(--mavi)' } as CSSProperties}
          >
            {ikon}
          </span>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginTop: 8 }}>
        <span className="kpi-deger">{deger}</span>
        {birim && <span style={{ color: 'var(--metin-soluk)', fontSize: 13 }}>{birim}</span>}
      </div>
      {(deltaMetin || altMetin) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 7,
            marginTop: 8,
            fontSize: 12.5,
          }}
        >
          {deltaMetin && (
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 3,
                color: deltaRenk,
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
      {seri && seri.length >= 2 && (
        <div style={{ marginTop: 10, marginInline: -2 }}>
          <MiniTrend seri={seri} renk={renk ?? 'var(--mavi)'} genislik="100%" yukseklik={30} />
        </div>
      )}
    </Card>
  );
}
