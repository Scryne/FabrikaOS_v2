/**
 * Persona çözücü birim testleri — izin + entitlement süzgeci ve persona etiketi mantığı.
 * "Her modül için farklı pano"nın çekirdeği: depo yalnız stok, yönetici tüm bento.
 */

import { describe, expect, it } from 'vitest';

import { gorunurWidgetlar, PANO_WIDGETLARI, personaAnahtari } from './personalar';

const izinSeti =
  (izinler: string[]) =>
  (izin: string): boolean =>
    izinler.includes(izin);

describe('gorunurWidgetlar + personaAnahtari', () => {
  it('depo persona yalnız stok + satınalma panellerini görür', () => {
    const w = gorunurWidgetlar(izinSeti(['stok:oku', 'satinalma:oku']));
    expect(w.map((x) => x.anahtar)).toEqual(['stok', 'satinalma']);
    expect(personaAnahtari(w)).toBe('pano.persona_depo');
  });

  it('kalite persona yalnız kalite panelini görür', () => {
    const w = gorunurWidgetlar(izinSeti(['kalite:oku']));
    expect(w.map((x) => x.anahtar)).toEqual(['kalite']);
    expect(personaAnahtari(w)).toBe('pano.persona_kalite');
  });

  it('tüm izinlerde tüm paneller görünür + yönetim personası', () => {
    const w = gorunurWidgetlar(izinSeti(PANO_WIDGETLARI.map((x) => x.izin)));
    expect(w).toHaveLength(PANO_WIDGETLARI.length);
    expect(personaAnahtari(w)).toBe('pano.persona_yonetim');
  });

  it('kapalı entitlement modülü paneli gizler', () => {
    const w = gorunurWidgetlar(izinSeti(['stok:oku', 'satinalma:oku']), (m) => m !== 'stok');
    expect(w).toHaveLength(0);
  });

  it('izin yoksa boş liste + genel persona', () => {
    const w = gorunurWidgetlar(izinSeti([]));
    expect(w).toHaveLength(0);
    expect(personaAnahtari(w)).toBe('pano.persona_genel');
  });
});
