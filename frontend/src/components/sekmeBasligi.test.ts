import { describe, expect, it } from 'vitest';

import { sekmeBasligiMetni } from './sekmeBasligi';

describe('sekmeBasligiMetni', () => {
  it('ekran adına ürün adını ekler, ad yoksa ürün adında kalır, ürün adını iki kez yazmaz', () => {
    expect(sekmeBasligiMetni('Kontrol planları')).toBe('Kontrol planları · FabrikaOS');
    expect(sekmeBasligiMetni(null)).toBe('FabrikaOS');
    expect(sekmeBasligiMetni('FabrikaOS Müşteri Portalı')).toBe('FabrikaOS Müşteri Portalı');
  });
});
