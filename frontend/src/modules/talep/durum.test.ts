import { describe, expect, it } from 'vitest';

import { gecerliHedefler, GECISLER, TERMINAL } from './durum';

describe('talep durum makinesi aynası', () => {
  it('acik → inceleniyor/iptal', () => {
    expect(gecerliHedefler('acik').sort()).toEqual(['inceleniyor', 'iptal']);
  });

  it('cozuldu → kapandi/yeniden inceleniyor', () => {
    expect(gecerliHedefler('cozuldu').sort()).toEqual(['inceleniyor', 'kapandi']);
  });

  it('terminaller çıkışsız', () => {
    for (const d of TERMINAL) expect(GECISLER[d]).toEqual([]);
  });
});
