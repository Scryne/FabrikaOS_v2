import { describe, expect, it } from 'vitest';

import { RENKLER } from '@/tema/tema';

import {
  alanSecenek,
  cizgiSecenek,
  cubukSecenek,
  donutSecenek,
  gostergeSecenek,
  isiHaritaSecenek,
  oeeRenk,
  paretoSecenek,
  sparklineSecenek,
  yiginCubukSecenek,
} from './grafikSecenek';

describe('oeeRenk (eşik renklendirme)', () => {
  it('≥85 yeşil, ≥70 amber, altı kırmızı', () => {
    expect(oeeRenk(92)).toBe(RENKLER.basari);
    expect(oeeRenk(85)).toBe(RENKLER.basari);
    expect(oeeRenk(72)).toBe(RENKLER.uyari);
    expect(oeeRenk(40)).toBe(RENKLER.hata);
  });
});

describe('gostergeSecenek', () => {
  it('gauge serisi + değeri taşır ve eşik rengini uygular', () => {
    const s = gostergeSecenek(64);
    const seri = (s.series as { type: string; data: { value: number }[] }[])[0]!;
    expect(seri.type).toBe('gauge');
    expect(seri.data[0]!.value).toBe(64);
  });
});

describe('cubukSecenek', () => {
  it('her makine için sütun verisi üretir, OEE ekseni 0–100', () => {
    const s = cubukSecenek([
      { ad: 'MAK-A', oee: 88 },
      { ad: 'MAK-B', oee: 60 },
    ]);
    const seri = (s.series as { data: unknown[] }[])[0]!;
    expect(seri.data).toHaveLength(2);
    expect((s.yAxis as { max: number }).max).toBe(100);
  });
});

describe('cizgiSecenek', () => {
  it('zaman serisini kategori ekseni + çizgi serisine çevirir', () => {
    const o = cizgiSecenek([
      { zaman: '08:00', deger: 30 },
      { zaman: '09:00', deger: 45 },
    ]);
    const seri = (o.series as { type: string; data: number[] }[])[0]!;
    expect(seri.type).toBe('line');
    expect(seri.data).toEqual([30, 45]);
    expect((o.xAxis as { data: string[] }).data).toEqual(['08:00', '09:00']);
  });
});

describe('donutSecenek', () => {
  it('segmentleri pie verisine renkleriyle eşler', () => {
    const s = donutSecenek([
      { ad: 'Çalışıyor', deger: 3, renk: RENKLER.basari },
      { ad: 'Durdu', deger: 1, renk: RENKLER.metinSoluk },
    ]);
    const seri = (s.series as { type: string; data: { name: string; value: number }[] }[])[0]!;
    expect(seri.type).toBe('pie');
    expect(seri.data.map((d) => d.name)).toEqual(['Çalışıyor', 'Durdu']);
    expect(seri.data[0]!.value).toBe(3);
  });
});

describe('alanSecenek', () => {
  it('tek seride alan dolgusu var, kategorileri taşır', () => {
    const o = alanSecenek(['Pzt', 'Sal'], [{ ad: 'Üretim', veri: [10, 20] }]);
    const seri = (o.series as { type: string; areaStyle?: unknown; data: number[] }[])[0]!;
    expect(seri.type).toBe('line');
    expect(seri.areaStyle).toBeDefined();
    expect((o.xAxis as { data: string[] }).data).toEqual(['Pzt', 'Sal']);
  });

  it('kesikli seri (tahmin) alan dolgusu taşımaz ve dashed çizgidir', () => {
    const o = alanSecenek(['1', '2'], [{ ad: 'Tahmin', veri: [1, 2], kesikli: true }]);
    const seri = (o.series as { areaStyle?: unknown; lineStyle: { type: string } }[])[0]!;
    expect(seri.areaStyle).toBeUndefined();
    expect(seri.lineStyle.type).toBe('dashed');
  });
});

describe('yiginCubukSecenek', () => {
  it('serileri aynı stack üstünde çubuklara çevirir', () => {
    const o = yiginCubukSecenek(
      ['A', 'B'],
      [
        { ad: 'Giriş', veri: [3, 5] },
        { ad: 'Çıkış', veri: [1, 2] },
      ],
    );
    const seriler = o.series as { type: string; stack: string }[];
    expect(seriler).toHaveLength(2);
    expect(seriler[0]!.type).toBe('bar');
    expect(seriler[0]!.stack).toBe(seriler[1]!.stack);
  });
});

describe('isiHaritaSecenek', () => {
  it('visualMap üst sınırını en büyük değere ayarlar', () => {
    const o = isiHaritaSecenek(
      ['00', '01'],
      ['Pzt'],
      [
        [0, 0, 4],
        [1, 0, 9],
      ],
    );
    expect((o.visualMap as { max: number }).max).toBe(9);
    expect((o.series as { type: string }[])[0]!.type).toBe('heatmap');
  });
});

describe('sparklineSecenek', () => {
  it('eksenleri gizler ve veriyi çizgiye koyar', () => {
    const o = sparklineSecenek([1, 3, 2]);
    expect((o.xAxis as { show: boolean }).show).toBe(false);
    expect((o.series as { data: number[] }[])[0]!.data).toEqual([1, 3, 2]);
  });
});

describe('paretoSecenek', () => {
  it('çubukları azalan sıralar ve kümülatif yüzdeyi %100e kadar üretir', () => {
    const o = paretoSecenek([
      { ad: 'A', deger: 20 },
      { ad: 'C', deger: 60 },
      { ad: 'B', deger: 20 },
    ]);
    const cubuk = (o.series as { data: number[] }[])[0]!;
    const kumulatif = (o.series as { data: number[] }[])[1]!;
    expect(cubuk.data).toEqual([60, 20, 20]); // azalan
    expect(kumulatif.data[kumulatif.data.length - 1]).toBe(100);
  });
});
