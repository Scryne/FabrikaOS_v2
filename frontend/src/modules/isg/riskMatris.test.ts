import { describe, expect, it } from 'vitest';

import { riskSeviyesi, riskSkoru } from './riskMatris';

describe('Risk matrisi aynası', () => {
  it('skor = olasılık × şiddet', () => {
    expect(riskSkoru(3, 4)).toBe(12);
    expect(riskSkoru(5, 5)).toBe(25);
  });
  it('seviye eşikleri backend ile aynı', () => {
    expect(riskSeviyesi(1)).toBe('dusuk');
    expect(riskSeviyesi(4)).toBe('dusuk');
    expect(riskSeviyesi(5)).toBe('orta');
    expect(riskSeviyesi(9)).toBe('orta');
    expect(riskSeviyesi(10)).toBe('yuksek');
    expect(riskSeviyesi(15)).toBe('yuksek');
    expect(riskSeviyesi(16)).toBe('cok_yuksek');
    expect(riskSeviyesi(25)).toBe('cok_yuksek');
  });
});
