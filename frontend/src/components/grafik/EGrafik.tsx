/**
 * İnce ECharts sarmalayıcısı — init / setOption / resize / dispose yaşam döngüsünü yönetir.
 *
 * Seçenekler ``grafikSecenek.ts`` saf üreticilerinden gelir (tek doğruluk kaynağı). Kapsayıcı
 * yeniden boyutlandığında grafik ``ResizeObserver`` ile otomatik ölçeklenir; unmount'ta
 * dispose edilir (bellek sızıntısı yok).
 */

import { useEffect, useRef } from 'react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';

export function EGrafik({
  secenek,
  yukseklik = 280,
  sinif,
}: {
  secenek: EChartsOption;
  yukseklik?: number | string;
  sinif?: string;
}) {
  const kapRef = useRef<HTMLDivElement>(null);
  const grafikRef = useRef<echarts.ECharts | null>(null);

  // Init + resize gözlemcisi (yalnız mount/unmount).
  useEffect(() => {
    const kap = kapRef.current;
    if (!kap) return;
    const grafik = echarts.init(kap, undefined, { renderer: 'canvas' });
    grafikRef.current = grafik;
    const gozlemci = new ResizeObserver(() => grafik.resize());
    gozlemci.observe(kap);
    return () => {
      gozlemci.disconnect();
      grafik.dispose();
      grafikRef.current = null;
    };
  }, []);

  // Seçenek değişince güncelle (notMerge=true: eski seriler temizlenir).
  useEffect(() => {
    grafikRef.current?.setOption(secenek, true);
  }, [secenek]);

  return (
    <div ref={kapRef} className={sinif} style={{ width: '100%', height: yukseklik }} role="img" />
  );
}
