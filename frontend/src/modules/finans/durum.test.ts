import { describe, expect, it } from 'vitest';

import { faturaToplami, gecerliHedefler, kalemTutari } from './durum';

describe('fatura durum makinesi', () => {
  it('taslak doğrudan kesilmez, onaydan geçer', () => {
    expect(gecerliHedefler('taslak')).not.toContain('kesildi');
    expect(gecerliHedefler('onay_bekliyor')).toEqual(['kesildi', 'taslak', 'iptal']);
    expect(gecerliHedefler('kapandi')).toEqual([]);
    expect(gecerliHedefler('bilinmeyen')).toEqual([]);
  });
});

describe('kalem tutarı (sunucuyla aynı yuvarlama)', () => {
  it('satır başına yarım yukarı, KDV yuvarlanmış satırdan', () => {
    expect(kalemTutari(3, 33.335, 20)).toEqual({ satir: 100.01, kdv: 20 });
    expect(kalemTutari(1, 0.05, 10)).toEqual({ satir: 0.05, kdv: 0.01 });
  });

  it('toplam sunucudaki örnekle aynı: 175,01', () => {
    expect(
      faturaToplami([
        { miktar: 3, birim_fiyat: 33.335, kdv_orani: 20 },
        { miktar: 1, birim_fiyat: 50, kdv_orani: 10 },
        { miktar: undefined, birim_fiyat: 10 },
      ]),
    ).toEqual({ ara: 150.01, kdv: 25, genel: 175.01 });
  });
});
