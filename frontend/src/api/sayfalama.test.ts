import { describe, expect, it } from 'vitest';

import { sorguDizesi, VARSAYILAN_SAYFA } from './sayfalama';

describe('sorguDizesi', () => {
  it('yalnız sayfa+adet ile temel dize üretir', () => {
    expect(sorguDizesi(VARSAYILAN_SAYFA)).toBe('sayfa=1&adet=20');
  });

  it('sıralama verilince yon de eklenir (varsayılan asc)', () => {
    expect(sorguDizesi({ sayfa: 1, adet: 20, siralama: 'kod' })).toBe(
      'sayfa=1&adet=20&siralama=kod&yon=asc',
    );
    expect(sorguDizesi({ sayfa: 1, adet: 20, siralama: 'kod', yon: 'desc' })).toContain('yon=desc');
  });

  it('boş/whitespace arama dizeye yazılmaz, dolu arama trimlenir', () => {
    expect(sorguDizesi({ sayfa: 1, adet: 20, arama: '   ' })).toBe('sayfa=1&adet=20');
    expect(sorguDizesi({ sayfa: 1, adet: 20, arama: '  pres ' })).toContain('arama=pres');
  });

  it('tanımsız/boş filtreleri atar, dolu filtreleri yazar', () => {
    const ds = sorguDizesi({
      sayfa: 2,
      adet: 50,
      filtreler: { durum: 'calisiyor', makine_id: 4, aktif: undefined, bos: '' },
    });
    expect(ds).toContain('sayfa=2');
    expect(ds).toContain('durum=calisiyor');
    expect(ds).toContain('makine_id=4');
    expect(ds).not.toContain('aktif');
    expect(ds).not.toContain('bos');
  });
});
