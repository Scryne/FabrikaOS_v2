import { describe, expect, it } from 'vitest';

import { MENU } from '@/layouts/menu';

import { MENU_IKONLARI } from './modulKimlik';

describe('MENU_IKONLARI', () => {
  it('her menü öğesinin bir ikonu var (kenar çubuğunda ikonsuz satır kalmaz)', () => {
    const eksik = MENU.map((o) => o.anahtar).filter((a) => !MENU_IKONLARI[a]);
    expect(eksik).toEqual([]);
  });
});
