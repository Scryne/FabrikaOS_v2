import { describe, expect, it } from 'vitest';

import { gecerliHedefler, terminalMi } from './durum';

describe('iş emri durum makinesi (istemci aynası)', () => {
  it('acik → atandi | iptal', () => {
    expect([...gecerliHedefler('acik')].sort()).toEqual(['atandi', 'iptal']);
  });

  it('atandi → devam_ediyor | iptal', () => {
    expect([...gecerliHedefler('atandi')].sort()).toEqual(['devam_ediyor', 'iptal']);
  });

  it('devam_ediyor → kapandi | iptal', () => {
    expect([...gecerliHedefler('devam_ediyor')].sort()).toEqual(['iptal', 'kapandi']);
  });

  it('terminal durumlardan çıkış yok', () => {
    expect(gecerliHedefler('kapandi')).toEqual([]);
    expect(gecerliHedefler('iptal')).toEqual([]);
    expect(terminalMi('kapandi')).toBe(true);
    expect(terminalMi('iptal')).toBe(true);
    expect(terminalMi('acik')).toBe(false);
  });

  it('bilinmeyen durum boş hedef döndürür', () => {
    expect(gecerliHedefler('ucan-daire')).toEqual([]);
  });
});
