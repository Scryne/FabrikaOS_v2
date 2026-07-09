/**
 * Küçük sparkline — KpiKart ve tablo hücrelerinde trend sinyali. ``EGrafik`` + saf
 * ``sparklineSecenek`` üstünde ince bir sarmalayıcı. 2'den az nokta varsa çizilmez.
 */

import { useMemo } from 'react';

import { EGrafik } from '@/components/grafik/EGrafik';
import { sparklineSecenek } from '@/components/grafik/grafikSecenek';

export function MiniTrend({
  seri,
  renk,
  yukseklik = 32,
  genislik = 92,
}: {
  seri: number[];
  renk?: string;
  yukseklik?: number;
  genislik?: number | string;
}) {
  const secenek = useMemo(() => sparklineSecenek(seri, renk), [seri, renk]);
  if (seri.length < 2) return null;
  return (
    <div style={{ width: genislik }}>
      <EGrafik secenek={secenek} yukseklik={yukseklik} />
    </div>
  );
}
