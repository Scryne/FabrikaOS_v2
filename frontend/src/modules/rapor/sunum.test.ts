import { describe, expect, it } from 'vitest';

import { boyutMetni, DURUM_RENK, indirilebilir, RAPOR_BICIMLERI, RAPOR_TURLERI } from './sunum';

describe('rapor sunum yardımcıları (backend birimler.py aynası)', () => {
  it('tür ve biçim beyaz-listeleri backend ile aynı', () => {
    expect([...RAPOR_TURLERI].sort()).toEqual(
      ['enerji', 'isemri', 'kalite', 'stok', 'uretim'].sort(),
    );
    expect([...RAPOR_BICIMLERI]).toEqual(['pdf', 'xlsx']);
  });

  it('her yaşam döngüsü durumu bir rozet rengine eşlenir', () => {
    for (const durum of ['kuyrukta', 'hazirlaniyor', 'hazir', 'basarisiz']) {
      expect(DURUM_RENK[durum], durum).toBeTruthy();
    }
  });

  it('yalnız hazir durumu indirilebilir', () => {
    expect(indirilebilir('hazir')).toBe(true);
    for (const durum of ['kuyrukta', 'hazirlaniyor', 'basarisiz']) {
      expect(indirilebilir(durum), durum).toBe(false);
    }
  });

  it('boyutMetni insan-okur birime çevirir', () => {
    expect(boyutMetni(0)).toBe('—');
    expect(boyutMetni(512)).toBe('512 B');
    expect(boyutMetni(2048)).toBe('2 KB');
    expect(boyutMetni(3 * 1024 * 1024)).toBe('3 MB');
  });
});
