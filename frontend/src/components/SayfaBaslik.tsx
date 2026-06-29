/** Ekran başlığı — başlık + opsiyonel alt metin (sol) ve sağ aksiyon alanı. Tutarlı üst boşluk. */

import type { ReactNode } from 'react';
import { Typography } from 'antd';

export function SayfaBaslik({
  baslik,
  alt,
  sag,
}: {
  baslik: ReactNode;
  alt?: ReactNode;
  sag?: ReactNode;
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 16,
        marginBottom: 22,
      }}
    >
      <div>
        <Typography.Title level={3} style={{ margin: 0, letterSpacing: '-0.02em' }}>
          {baslik}
        </Typography.Title>
        {alt && (
          <Typography.Paragraph style={{ color: 'var(--metin-soluk)', margin: '4px 0 0' }}>
            {alt}
          </Typography.Paragraph>
        )}
      </div>
      {sag && <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>{sag}</div>}
    </div>
  );
}
