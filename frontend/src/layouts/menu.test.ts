import { describe, expect, it } from 'vitest';

import { gorunurMenu, MENU } from './menu';

describe('gorunurMenu (RBAC menü filtresi)', () => {
  it('izin gerektirmeyen öğe (pano) her zaman görünür', () => {
    const gorunur = gorunurMenu(MENU, () => false);
    expect(gorunur.map((o) => o.anahtar)).toEqual(['pano']);
  });

  it('yalnız sahip olunan izinli öğeler görünür', () => {
    const izinli = new Set(['uretim:oku']);
    const gorunur = gorunurMenu(MENU, (izin) => izinli.has(izin));
    expect(gorunur.map((o) => o.anahtar)).toEqual(['pano', 'makineler']);
  });

  it('tam yetkili kullanıcı tüm öğeleri görür', () => {
    const gorunur = gorunurMenu(MENU, () => true);
    expect(gorunur).toHaveLength(MENU.length);
  });
});
