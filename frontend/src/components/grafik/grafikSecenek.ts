/**
 * ECharts seçenek üreticileri (saf fonksiyonlar) — koyu nötr temaya göre.
 *
 * Bileşenlerden ayrı tutulur ki birim testlenebilsinler ve render'dan bağımsız olsunlar.
 * Renkler ``tema.ts`` tek doğruluk kaynağından gelir.
 */

import type { EChartsOption } from 'echarts';

import { sayiMetni, sayiSabit } from '@/i18n/sayi';
import { GRAFIK_PALETI, RENKLER } from '@/tema/tema';

/** Değer ekseni etiketleri etkin dilin biçimiyle (echarts varsayılanı "1,200" yazar). */
const eksenSayisi = (v: number) => sayiMetni(v);

const MONO = "'JetBrains Mono Variable', ui-monospace, monospace";
const GOVDE = "'Inter Variable', system-ui, sans-serif";
const IZGARA_RENK = 'rgba(255,255,255,0.06)';

/** ``#rrggbb`` → ``rgba(r,g,b,a)`` (canvas degrade dolgusu için; saf, echarts'sız). */
function rgba(hex: string, alfa: number): string {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alfa})`;
}

/** Koyu nötr temaya uygun ortak ipucu (tooltip) tabanı. */
function koyuIpucu(trigger: 'axis' | 'item'): NonNullable<EChartsOption['tooltip']> {
  return {
    trigger,
    backgroundColor: RENKLER.yuzeyUst,
    borderColor: RENKLER.kenarlik,
    textStyle: { color: RENKLER.metin, fontFamily: GOVDE },
  };
}

/** Bir seri: etiket + değerler (+ opsiyonel renk / kesikli çizgi — tahmin ufku gibi). */
export type SeriVeri = {
  ad: string;
  veri: (number | null)[];
  renk?: string;
  /** Kesikli çizgi (ör. OEE tahmini "gelecek" kısmı). */
  kesikli?: boolean;
};

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
      // `interval: 0` 390 px'de 12 makine adını üst üste basıyordu; otomatik aralık geniş
      // ekranda hepsini, dar ekranda sığanları gösterir (tam ad ipucunda).
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: GOVDE, fontSize: 11, hideOverlap: true },
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

/** Zaman serisi çizgi grafiği (ör. enerji tüketim trendi). ``deger`` y ekseni değeri. */
export function cizgiSecenek(veri: { zaman: string; deger: number }[]): EChartsOption {
  return {
    grid: { left: 6, right: 14, top: 18, bottom: 4, containLabel: true },
    tooltip: {
      trigger: 'axis',
      backgroundColor: RENKLER.yuzeyUst,
      borderColor: RENKLER.kenarlik,
      textStyle: { color: RENKLER.metin, fontFamily: GOVDE },
    },
    xAxis: {
      type: 'category',
      data: veri.map((v) => v.zaman),
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: GOVDE, fontSize: 11 },
      axisLine: { lineStyle: { color: RENKLER.kenarlik } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      splitLine: { lineStyle: { color: IZGARA_RENK } },
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: MONO, formatter: eksenSayisi },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        showSymbol: false,
        areaStyle: { opacity: 0.12, color: RENKLER.cyan },
        lineStyle: { color: RENKLER.cyan, width: 2 },
        itemStyle: { color: RENKLER.cyan },
        data: veri.map((v) => v.deger),
      },
    ],
  };
}

/**
 * Degrade dolgulu alan/çizgi grafiği (bir veya çok seri). Trend panolarının imzası:
 * çizgi + üstten alta sönümlenen renkli dolgu. ``kesikli`` seriler tahmin ufkunu gösterir.
 */
export function alanSecenek(kategoriler: string[], seriler: SeriVeri[]): EChartsOption {
  const cokSeri = seriler.length > 1;
  return {
    grid: { left: 6, right: 14, top: cokSeri ? 30 : 18, bottom: 4, containLabel: true },
    tooltip: koyuIpucu('axis'),
    legend: cokSeri
      ? { top: 0, right: 0, textStyle: { color: RENKLER.metinSoluk }, icon: 'roundRect' }
      : undefined,
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: kategoriler,
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: GOVDE, fontSize: 11 },
      axisLine: { lineStyle: { color: RENKLER.kenarlik } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: 0,
      splitLine: { lineStyle: { color: IZGARA_RENK } },
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: MONO, formatter: eksenSayisi },
    },
    series: seriler.map((s, i) => {
      const renk = s.renk ?? GRAFIK_PALETI[i % GRAFIK_PALETI.length]!;
      return {
        name: s.ad,
        type: 'line',
        smooth: true,
        showSymbol: false,
        connectNulls: false,
        lineStyle: { color: renk, width: 2, type: s.kesikli ? 'dashed' : 'solid' },
        itemStyle: { color: renk },
        areaStyle: s.kesikli
          ? undefined
          : {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: rgba(renk, 0.28) },
                  { offset: 1, color: rgba(renk, 0) },
                ],
              },
            },
        data: s.veri,
      };
    }),
  };
}

/** Yığın çubuk grafiği (ör. stok giriş/çıkış, makine bazlı üretim kırılımı). */
export function yiginCubukSecenek(kategoriler: string[], seriler: SeriVeri[]): EChartsOption {
  return {
    grid: { left: 6, right: 14, top: 30, bottom: 4, containLabel: true },
    tooltip: koyuIpucu('axis'),
    legend: { top: 0, right: 0, textStyle: { color: RENKLER.metinSoluk }, icon: 'roundRect' },
    xAxis: {
      type: 'category',
      data: kategoriler,
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: GOVDE, fontSize: 11 },
      axisLine: { lineStyle: { color: RENKLER.kenarlik } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: IZGARA_RENK } },
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: MONO, formatter: eksenSayisi },
    },
    series: seriler.map((s, i) => ({
      name: s.ad,
      type: 'bar',
      stack: 'toplam',
      barWidth: '52%',
      itemStyle: { color: s.renk ?? GRAFIK_PALETI[i % GRAFIK_PALETI.length]! },
      data: s.veri,
    })),
  };
}

/**
 * Isı haritası (ör. saat × gün üretim/enerji yoğunluğu). ``veri`` [xIndex, yIndex, değer]
 * üçlüleri; renk nötr yüzeyden ``accentRenk`` aksanına yükselir (sıralı skala).
 */
export function isiHaritaSecenek(
  xEtiketler: string[],
  yEtiketler: string[],
  veri: [number, number, number][],
  accentRenk: string = RENKLER.cyan,
): EChartsOption {
  const enBuyuk = veri.reduce((m, v) => Math.max(m, v[2]), 0);
  return {
    grid: { left: 6, right: 10, top: 10, bottom: 40, containLabel: true },
    tooltip: koyuIpucu('item'),
    xAxis: {
      type: 'category',
      data: xEtiketler,
      splitArea: { show: false },
      axisLabel: {
        color: RENKLER.metinSoluk,
        fontFamily: MONO,
        fontSize: 10,
      },
      axisLine: { lineStyle: { color: RENKLER.kenarlik } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'category',
      data: yEtiketler,
      splitArea: { show: false },
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: GOVDE, fontSize: 11 },
      axisLine: { lineStyle: { color: RENKLER.kenarlik } },
      axisTick: { show: false },
    },
    visualMap: {
      min: 0,
      max: enBuyuk || 1,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      itemWidth: 12,
      itemHeight: 120,
      textStyle: { color: RENKLER.metinSoluk, fontFamily: MONO, fontSize: 10 },
      inRange: { color: [rgba(accentRenk, 0.06), rgba(accentRenk, 0.5), accentRenk] },
    },
    series: [
      {
        type: 'heatmap',
        data: veri,
        itemStyle: { borderColor: RENKLER.zemin, borderWidth: 2, borderRadius: 3 },
        emphasis: { itemStyle: { borderColor: RENKLER.kenarlikParlak } },
      },
    ],
  };
}

/** Küçük sparkline (eksen/ızgara yok) — KpiKart ve tablo hücreleri için. */
export function sparklineSecenek(veri: number[], renk: string = RENKLER.cyan): EChartsOption {
  return {
    grid: { left: 1, right: 1, top: 3, bottom: 1 },
    xAxis: { type: 'category', show: false, boundaryGap: false, data: veri.map((_, i) => i) },
    yAxis: { type: 'value', show: false, min: 'dataMin', max: 'dataMax' },
    series: [
      {
        type: 'line',
        smooth: true,
        showSymbol: false,
        silent: true,
        lineStyle: { color: renk, width: 1.6 },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: rgba(renk, 0.24) },
              { offset: 1, color: rgba(renk, 0) },
            ],
          },
        },
        data: veri,
      },
    ],
  };
}

/**
 * Pareto grafiği (kalite hata türü / duruş nedeni) — çubuklar azalan sıralı + ikincil
 * eksende kümülatif yüzde çizgisi. Girdi sıralanmamış olabilir; burada azalan sıralanır.
 */
export function paretoSecenek(veri: { ad: string; deger: number }[]): EChartsOption {
  const sirali = [...veri].sort((a, b) => b.deger - a.deger);
  const toplam = sirali.reduce((s, v) => s + v.deger, 0) || 1;
  let birikimli = 0;
  const kumulatif = sirali.map((v) => {
    birikimli += v.deger;
    return Math.round((birikimli / toplam) * 100);
  });
  return {
    grid: { left: 6, right: 6, top: 24, bottom: 4, containLabel: true },
    tooltip: koyuIpucu('axis'),
    xAxis: {
      type: 'category',
      data: sirali.map((v) => v.ad),
      // `interval: 0` 390 px'de 12 makine adını üst üste basıyordu; otomatik aralık geniş
      // ekranda hepsini, dar ekranda sığanları gösterir (tam ad ipucunda).
      axisLabel: { color: RENKLER.metinSoluk, fontFamily: GOVDE, fontSize: 11, hideOverlap: true },
      axisLine: { lineStyle: { color: RENKLER.kenarlik } },
      axisTick: { show: false },
    },
    yAxis: [
      {
        type: 'value',
        splitLine: { lineStyle: { color: IZGARA_RENK } },
        axisLabel: { color: RENKLER.metinSoluk, fontFamily: MONO, formatter: eksenSayisi },
      },
      {
        type: 'value',
        min: 0,
        max: 100,
        splitLine: { show: false },
        axisLabel: { color: RENKLER.metinSoluk, fontFamily: MONO, formatter: '%{value}' },
      },
    ],
    series: [
      {
        type: 'bar',
        barWidth: '52%',
        itemStyle: { color: RENKLER.mor, borderRadius: [6, 6, 0, 0] },
        data: sirali.map((v) => v.deger),
      },
      {
        type: 'line',
        yAxisIndex: 1,
        smooth: false,
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { color: RENKLER.uyari, width: 2 },
        itemStyle: { color: RENKLER.uyari },
        data: kumulatif,
      },
    ],
  };
}

/**
 * SPC kontrol kartı (S26): noktalar + merkez çizgi + üst/alt kontrol limitleri (kesikli).
 * İhlal eden noktalar kırmızı ve büyük; ipucunda alt grup sırası ve değer görünür. Tolerans
 * çizgileri (ölçüm spesifikasyonu) yalnız X̄ kartında ve ayrı bir renkte: kontrol limiti ile
 * spesifikasyon limiti karıştırılmasın (kalite eğitiminin en sık hatası).
 */
export function kontrolKartiSecenek(girdi: {
  siralar: number[];
  degerler: number[];
  cl: number;
  ucl: number;
  lcl: number;
  ihlalIndeksleri: Set<number>;
  ondalik?: number;
  tolerans?: { alt: number | null; ust: number | null };
  etiketler: { cl: string; ucl: string; lcl: string; alt?: string; ust?: string };
}): EChartsOption {
  const { siralar, degerler, cl, ucl, lcl, ihlalIndeksleri, tolerans, etiketler } = girdi;
  const ondalik = girdi.ondalik ?? 3;
  const yatay = (y: number, ad: string, renk: string, kesikli: boolean) => ({
    yAxis: y,
    name: ad,
    lineStyle: { color: renk, type: kesikli ? ('dashed' as const) : ('solid' as const), width: 1 },
    label: {
      formatter: `${ad} ${sayiSabit(y, ondalik)}`,
      color: renk,
      fontFamily: MONO,
      fontSize: 10,
      position: 'insideEndTop' as const,
    },
  });
  const cizgiler = [
    yatay(cl, etiketler.cl, RENKLER.metinSoluk, false),
    yatay(ucl, etiketler.ucl, RENKLER.uyari, true),
    yatay(lcl, etiketler.lcl, RENKLER.uyari, true),
  ];
  if (tolerans?.alt != null)
    cizgiler.push(yatay(tolerans.alt, etiketler.alt ?? 'ASL', RENKLER.mor, true));
  if (tolerans?.ust != null)
    cizgiler.push(yatay(tolerans.ust, etiketler.ust ?? 'ÜSL', RENKLER.mor, true));
  const tumY = [
    ...degerler,
    ucl,
    lcl,
    ...(tolerans?.alt != null ? [tolerans.alt] : []),
    ...(tolerans?.ust != null ? [tolerans.ust] : []),
  ];
  const enKucuk = Math.min(...tumY);
  const enBuyuk = Math.max(...tumY);
  const pay = (enBuyuk - enKucuk) * 0.08 || 1;
  return {
    animation: false,
    grid: { left: 6, right: 16, top: 16, bottom: 4, containLabel: true },
    tooltip: {
      ...koyuIpucu('axis'),
      valueFormatter: (v) => (typeof v === 'number' ? sayiSabit(v, ondalik) : String(v)),
    },
    xAxis: {
      type: 'category',
      data: siralar.map(String),
      axisLabel: {
        color: RENKLER.metinSoluk,
        fontFamily: MONO,
        fontSize: 10,
      },
      axisLine: { lineStyle: { color: RENKLER.kenarlik } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      min: Number((enKucuk - pay).toFixed(ondalik)),
      max: Number((enBuyuk + pay).toFixed(ondalik)),
      splitLine: { lineStyle: { color: IZGARA_RENK } },
      axisLabel: {
        color: RENKLER.metinSoluk,
        fontFamily: MONO,
        fontSize: 10,
        formatter: eksenSayisi,
      },
    },
    series: [
      {
        type: 'line',
        data: degerler.map((d, i) => ({
          value: d,
          symbolSize: ihlalIndeksleri.has(i) ? 10 : 5,
          itemStyle: { color: ihlalIndeksleri.has(i) ? RENKLER.hata : RENKLER.cyan },
        })),
        lineStyle: { color: RENKLER.cyan, width: 1.5 },
        symbol: 'circle',
        markLine: { symbol: 'none', silent: true, data: cizgiler },
      },
    ],
  };
}
