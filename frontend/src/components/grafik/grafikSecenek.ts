/**
 * ECharts seçenek üreticileri (saf fonksiyonlar) — koyu nötr temaya göre.
 *
 * Bileşenlerden ayrı tutulur ki birim testlenebilsinler ve render'dan bağımsız olsunlar.
 * Renkler ``tema.ts`` tek doğruluk kaynağından gelir.
 */

import type { EChartsOption } from 'echarts';

import { RENKLER } from '@/tema/tema';

const MONO = "'JetBrains Mono Variable', ui-monospace, monospace";
const GOVDE = "'Inter Variable', system-ui, sans-serif";
const IZGARA_RENK = 'rgba(255,255,255,0.06)';

/** OEE yüzdesine göre semantik renk (≥85 yeşil, ≥70 amber, altı kırmızı). */
export function oeeRenk(yuzde: number): string {
  if (yuzde >= 85) return RENKLER.basari;
  if (yuzde >= 70) return RENKLER.uyari;
  return RENKLER.hata;
}

/** Tek değerli filo OEE göstergesi (gauge). ``yuzde`` 0–100. */
export function gostergeSecenek(yuzde: number): EChartsOption {
  const renk = oeeRenk(yuzde);
  return {
    series: [
      {
        type: 'gauge',
        startAngle: 220,
        endAngle: -40,
        min: 0,
        max: 100,
        radius: '96%',
        center: ['50%', '56%'],
        progress: { show: true, width: 12, roundCap: true, itemStyle: { color: renk } },
        axisLine: { lineStyle: { width: 12, color: [[1, 'rgba(255,255,255,0.08)']] } },
        axisTick: { show: false },
        splitLine: { show: false },
        axisLabel: { show: false },
        pointer: { show: false },
        anchor: { show: false },
        title: { show: false },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, '2%'],
          formatter: (v: number) => `%${Math.round(v)}`,
          color: RENKLER.metin,
          fontSize: 34,
          fontWeight: 700,
          fontFamily: MONO,
        },
        data: [{ value: yuzde }],
      },
    ],
  };
}

/** Makine bazlı OEE sütun grafiği. Her sütun OEE eşiğine göre renklenir. */
export function cubukSecenek(veri: { ad: string; oee: number }[]): EChartsOption {
  return {
    grid: { left: 6, right: 14, top: 18, bottom: 4, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: RENKLER.yuzeyUst,
      borderColor: RENKLER.kenarlik,
      textStyle: { color: RENKLER.metin, fontFamily: GOVDE },
      valueFormatter: (v) => `%${Math.round(Number(v))}`,
    },
    xAxis: {
      type: 'category',
      data: veri.map((v) => v.ad),
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: GOVDE, fontSize: 11, interval: 0 },
      axisLine: { lineStyle: { color: RENKLER.kenarlik } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      max: 100,
      splitLine: { lineStyle: { color: IZGARA_RENK } },
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: MONO, formatter: '%{value}' },
    },
    series: [
      {
        type: 'bar',
        barWidth: '46%',
        data: veri.map((v) => ({ value: v.oee, itemStyle: { color: oeeRenk(v.oee) } })),
        itemStyle: { borderRadius: [6, 6, 0, 0] },
      },
    ],
  };
}

export type DonutSegment = { ad: string; deger: number; renk: string };

/** Kategorik dağılım halkası (ör. makine durum kırılımı). Merkez boş bırakılır. */
export function donutSecenek(segmentler: DonutSegment[]): EChartsOption {
  return {
    tooltip: {
      trigger: 'item',
      backgroundColor: RENKLER.yuzeyUst,
      borderColor: RENKLER.kenarlik,
      textStyle: { color: RENKLER.metin, fontFamily: GOVDE },
      formatter: '{b}: {c}',
    },
    series: [
      {
        type: 'pie',
        radius: ['60%', '86%'],
        avoidLabelOverlap: false,
        label: { show: false },
        labelLine: { show: false },
        itemStyle: { borderColor: RENKLER.yuzey, borderWidth: 2 },
        data: segmentler.map((s) => ({
          name: s.ad,
          value: s.deger,
          itemStyle: { color: s.renk },
        })),
      },
    ],
  };
}
