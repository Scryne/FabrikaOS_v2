import { describe, expect, it } from 'vitest';

import { gecerliHedefler, TERMINAL } from './izinDurum';

describe('İzin talebi durum aynası', () => {
  it('taslak hedefleri backend ile aynı', () => {
    expect(gecerliHedefler('taslak')).toEqual(['onay_bekliyor', 'iptal']);
  });
  it('onay_bekliyor onayla/reddet/iptal', () => {
    expect(gecerliHedefler('onay_bekliyor')).toEqual(['onaylandi', 'reddedildi', 'iptal']);
  });
  it('terminal durumdan çıkış yok', () => {
    for (const d of TERMINAL) expect(gecerliHedefler(d)).toEqual([]);
  });
  it('bilinmeyen durum boş', () => {
    expect(gecerliHedefler('yok')).toEqual([]);
  });
});
