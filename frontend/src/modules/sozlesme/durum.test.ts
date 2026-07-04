import { describe, expect, it } from 'vitest';

import { gecerliHedefler, GECISLER, TERMINAL } from './durum';

describe('sözleşme durum makinesi aynası', () => {
  it('taslak yalnız aktif/iptal', () => {
    expect(gecerliHedefler('taslak').sort()).toEqual(['aktif', 'iptal']);
  });

  it('aktif → sonlandi/feshedildi/iptal', () => {
    expect(gecerliHedefler('aktif').sort()).toEqual(['feshedildi', 'iptal', 'sonlandi']);
  });

  it('terminaller çıkışsız', () => {
    for (const d of TERMINAL) expect(GECISLER[d]).toEqual([]);
  });

  it('bilinmeyen durum boş', () => {
    expect(gecerliHedefler('uzay')).toEqual([]);
  });
});
