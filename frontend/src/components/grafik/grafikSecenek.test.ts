import { describe, expect, it } from 'vitest';

import { RENKLER } from '@/tema/tema';

import { cubukSecenek, donutSecenek, gostergeSecenek, oeeRenk } from './grafikSecenek';

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
