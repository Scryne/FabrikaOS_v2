/**
 * Ekran başlığı — modül kimlikli: hat rengi plakasında modül ikonu + bölüm kırıntısı +
 * başlık + opsiyonel alt metin (sol) ve sağ aksiyon alanı. Kimlik rotadan otomatik çözülür
 * (tema/modulKimlik); router dışı render'da (test) sakin varsayılana düşer.
 */

import type { CSSProperties, ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { useInRouterContext, useLocation } from 'react-router-dom';
import { Typography } from 'antd';

import { yolKimlik, type ModulKimlik } from '@/tema/modulKimlik';

function BaslikGovde({
  baslik,
  alt,
  sag,
  kimlik,
}: {
  baslik: ReactNode;
  alt?: ReactNode;
  sag?: ReactNode;
  kimlik: ModulKimlik;
}) {
  const { t } = useTranslation();
  return (
    <div
      style={
        {
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 16,
          marginBottom: 24,
          '--plaka-renk': kimlik.renk,
        } as CSSProperties
      }
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14, minWidth: 0 }}>
        <span className="ikon-plaka" aria-hidden="true" style={{ marginTop: 3 }}>
          {kimlik.ikon}
        </span>
        <div style={{ minWidth: 0 }}>
          <div className="sayfa-kirinti">
            <span className="kirinti-nokta" aria-hidden="true" />
            {t(kimlik.bolum)}
          </div>
          <Typography.Title level={3} style={{ margin: 0, letterSpacing: '-0.02em' }}>
            {baslik}
          </Typography.Title>
          {alt && (
            <Typography.Paragraph
              style={{ color: 'var(--metin-soluk)', margin: '4px 0 0', maxWidth: '72ch' }}
            >
              {alt}
            </Typography.Paragraph>
          )}
        </div>
      </div>
      {/* Dar ekranda görünüm geçişi + aksiyonlar alt satıra kırılır (kırılmazsa sayfayı
          yatay kaydırıyordu: vardiya/duruş 390 px'de +160 px). */}
      {sag && (
        <div
          className="sayfa-baslik-sag"
          style={{
            display: 'flex',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 12,
            maxWidth: '100%',
          }}
        >
          {sag}
        </div>
      )}
    </div>
  );
}

function RotaliBaslik(props: { baslik: ReactNode; alt?: ReactNode; sag?: ReactNode }) {
  const konum = useLocation();
  return <BaslikGovde {...props} kimlik={yolKimlik(konum.pathname)} />;
}

export function SayfaBaslik(props: { baslik: ReactNode; alt?: ReactNode; sag?: ReactNode }) {
  // Router dışı render (ör. bileşen birim testi) — kimlik varsayılana düşer.
  const routerIcinde = useInRouterContext();
  if (!routerIcinde) return <BaslikGovde {...props} kimlik={yolKimlik('/')} />;
  return <RotaliBaslik {...props} />;
}
