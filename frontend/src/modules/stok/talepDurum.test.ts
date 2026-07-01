import { describe, expect, it } from 'vitest';

import { gecerliHedefler, TERMINAL } from './talepDurum';

describe('satınalma talebi durum aynası', () => {
  it('taslak → onay_bekliyor / iptal', () => {
    expect(gecerliHedefler('taslak')).toEqual(['onay_bekliyor', 'iptal']);
  });
  it('onay_bekliyor → onaylandi / reddedildi / iptal', () => {
    expect(gecerliHedefler('onay_bekliyor')).toEqual(['onaylandi', 'reddedildi', 'iptal']);
  });
  it('terminal durumlardan çıkış yok', () => {
    for (const d of TERMINAL) expect(gecerliHedefler(d)).toEqual([]);
  });
});
