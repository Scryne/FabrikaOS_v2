import { describe, expect, it } from 'vitest';

import type { components } from '@/api/types.gen';

import { durumDagilimi, filoOrtalamalari, makineOeeCubuklari } from './panoVeri';

type OeeOzetSatir = components['schemas']['OeeOzetSatirDTO'];
type Makine = components['schemas']['MakineCevapDTO'];

function ozet(p: Partial<OeeOzetSatir>): OeeOzetSatir {
  return {
    makine_id: 1,
    makine_kod: 'MAK',
    kullanilabilirlik: 0,
    performans: 0,
    kalite: 0,
    oee: 0,
    kayit_sayisi: 1,
    ...p,
  };
}

function makine(durum: string, id = 1): Makine {
  return { id, kod: `MAK-${id}`, ad: 'X', durum, oee_hedefi: null };
}

describe('filoOrtalamalari', () => {
  it('boş özet sıfır döndürür', () => {
    expect(filoOrtalamalari([])).toEqual({
      oee: 0,
      kullanilabilirlik: 0,
      performans: 0,
      kalite: 0,
    });
  });

  it('oranları yüzdeye çevirip ortalar', () => {
    const f = filoOrtalamalari([ozet({ oee: 0.8, kalite: 1.0 }), ozet({ oee: 0.6, kalite: 0.9 })]);
    expect(f.oee).toBeCloseTo(70);
    expect(f.kalite).toBeCloseTo(95);
  });
});

describe('durumDagilimi', () => {
  it('bilinen durumları sayar ve hepsini içerir', () => {
    const d = durumDagilimi([makine('calisiyor', 1), makine('calisiyor', 2), makine('ariza', 3)]);
    const harita = new Map(d.map((x) => [x.durum, x.adet]));
    expect(harita.get('calisiyor')).toBe(2);
    expect(harita.get('ariza')).toBe(1);
    expect(harita.get('durdu')).toBe(0);
  });
});

describe('makineOeeCubuklari', () => {
  it('kod + yüzde eşler ve limitler', () => {
    const c = makineOeeCubuklari(
      [ozet({ makine_kod: 'A', oee: 0.9 }), ozet({ makine_kod: 'B', oee: 0.5 })],
      1,
    );
    expect(c).toEqual([{ ad: 'A', oee: 90 }]);
  });
});
