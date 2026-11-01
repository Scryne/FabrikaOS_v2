/**
 * İnce ECharts sarmalayıcısı — init / setOption / resize / dispose yaşam döngüsünü yönetir.
 *
 * Seçenekler ``grafikSecenek.ts`` saf üreticilerinden gelir (tek doğruluk kaynağı). Kapsayıcı
 * yeniden boyutlandığında grafik ``ResizeObserver`` ile otomatik ölçeklenir; unmount'ta
 * dispose edilir (bellek sızıntısı yok). Tuval ekran okuyucuya görünmez; ``role="img"`` için
 * erişilebilir ad ``etiket``ten, yoksa seçenekteki başlıktan gelir (S27-B, WCAG 1.1.1).
 */

import { useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';

/** Seçenekteki ilk başlık metni (``title`` tekil ya da dizi olabilir). */
function baslikMetni(secenek: EChartsOption): string | undefined {
  const b = Array.isArray(secenek.title) ? secenek.title[0] : secenek.title;
  const metin = b && typeof b === 'object' && 'text' in b ? b.text : undefined;
  return typeof metin === 'string' && metin ? metin : undefined;
}

export function EGrafik({
  secenek,
  yukseklik = 280,
  sinif,
  etiket,
}: {
  secenek: EChartsOption;
  yukseklik?: number | string;
  sinif?: string;
  /** Ekran okuyucu için grafiğin ne gösterdiği. */
  etiket?: string;
}) {
  const { t } = useTranslation();
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
    <div
      ref={kapRef}
      className={sinif}
      style={{ width: '100%', height: yukseklik }}
      role="img"
      aria-label={etiket ?? baslikMetni(secenek) ?? t('grafik.etiket')}
    />
  );
}
