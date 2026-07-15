import { describe, expect, it } from 'vitest';

import { gorunurMenu, MENU } from './menu';

describe('gorunurMenu (RBAC menü filtresi)', () => {
  it('izin gerektirmeyen öğe (pano) her zaman görünür', () => {
    const gorunur = gorunurMenu(MENU, () => false);
    expect(gorunur.map((o) => o.anahtar)).toEqual(['pano', 'bildirim-tercihleri']);
  });

  it('yalnız sahip olunan izinli öğeler görünür', () => {
    const izinli = new Set(['uretim:oku']);
    const gorunur = gorunurMenu(MENU, (izin) => izinli.has(izin));
    expect(gorunur.map((o) => o.anahtar)).toEqual([
      'pano',
      'makineler',
      'uretim-verileri',
      'urunler',
      'vardiya-durus',
      'izlenebilirlik',
      'ikiz',
      'bildirim-tercihleri',
    ]);
  });

  it('tam yetkili kullanıcı tüm öğeleri görür', () => {
    const gorunur = gorunurMenu(MENU, () => true);
    expect(gorunur).toHaveLength(MENU.length);
  });

  it('kapalı entitlement modülünün öğeleri gizlenir (S16)', () => {
    const gorunur = gorunurMenu(
      MENU,
      () => true,
      (modul) => modul !== 'ai',
    );
    expect(gorunur.map((o) => o.anahtar)).not.toContain('tahminler');
    // ai dışındaki her şey durur (tahminler tek ai öğesi).
    expect(gorunur).toHaveLength(MENU.length - 1);
  });

  it('modul suzgeci verilmezse entitlement uygulanmaz (fail-open)', () => {
    const gorunur = gorunurMenu(MENU, () => true);
    expect(gorunur.map((o) => o.anahtar)).toContain('tahminler');
  });

  it('modülsüz çekirdek öğeler (pano, kullanıcılar, abonelik) süzgeçten etkilenmez', () => {
    const gorunur = gorunurMenu(
      MENU,
      () => true,
      () => false, // her modül kapalı
    );
    expect(gorunur.map((o) => o.anahtar)).toEqual([
      'pano',
      'kullanicilar',
      'abonelik',
      'bildirim-tercihleri',
    ]);
  });
});
