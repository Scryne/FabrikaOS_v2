import { describe, expect, it } from 'vitest';

import { AKTIF, gecerliHedefler, TERMINAL } from './durum';

describe('CAPA durum aynası', () => {
  it('acik hedefleri backend ile aynı', () => {
    expect(gecerliHedefler('acik')).toEqual(['kok_neden', 'iptal']);
  });
  it('dogrulama geri dönüş içerir', () => {
    expect(gecerliHedefler('dogrulama')).toEqual(['kapandi', 'uygulama', 'iptal']);
  });
  it('terminal durumdan çıkış yok', () => {
    for (const d of TERMINAL) expect(gecerliHedefler(d)).toEqual([]);
  });
  it('aktif durumlar terminal olmayanlar', () => {
    expect(AKTIF).toEqual(['acik', 'kok_neden', 'aksiyon_plani', 'uygulama', 'dogrulama']);
  });
  it('bilinmeyen durum boş', () => {
    expect(gecerliHedefler('yok')).toEqual([]);
  });
});
