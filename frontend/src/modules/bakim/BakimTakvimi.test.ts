import { describe, expect, it } from 'vitest';

import type { IzinTalebi } from '@/modules/ik/hooks';

import type { BakimPlani } from './hooks';
import { takvimGirdileri } from './BakimTakvimi';

function plan(kismi: Partial<BakimPlani>): BakimPlani {
  return {
    id: 1,
    ad: 'Aylık yağlama',
    makine_id: 1,
    tip: 'periyodik',
    periyot_gun: 30,
    son_bakim_tarihi: null,
    sonraki_bakim_tarihi: '2026-07-20T00:00:00Z',
    aciklama: '',
    aktif: true,
    olusturma_tarihi: '2026-07-01T00:00:00Z',
    ...kismi,
  } as BakimPlani;
}

function izin(kismi: Partial<IzinTalebi>): IzinTalebi {
  return {
    id: 1,
    kod: 'IZ-2026-000001',
    personel_id: 1,
    izin_turu: 'yillik',
    baslangic_tarihi: '2026-07-21',
    bitis_tarihi: '2026-07-23',
    gun_sayisi: 3,
    aciklama: '',
    durum: 'onaylandi',
    talep_eden_kullanici_id: null,
    onaylayan_kullanici_id: null,
    onay_tarihi: null,
    red_nedeni: '',
    olusturma_tarihi: '2026-07-01T00:00:00Z',
    ...kismi,
  } as IzinTalebi;
}

describe('takvimGirdileri', () => {
  it('aktif planın sonraki bakımını gününe yazar; pasif/tarihi olmayan plan atlanır', () => {
    const harita = takvimGirdileri(
      [
        plan({}),
        plan({ id: 2, ad: 'Pasif plan', aktif: false }),
        plan({ id: 3, ad: 'Tarihsiz', sonraki_bakim_tarihi: null }),
      ],
      [],
    );
    expect(harita.get('2026-07-20')).toEqual([{ tur: 'bakim', etiket: 'Aylık yağlama' }]);
    expect(harita.size).toBe(1);
  });

  it('onaylı izni başlangıç–bitiş aralığına gün gün yayar; onaysız izni almaz', () => {
    const harita = takvimGirdileri(
      [],
      [izin({}), izin({ id: 2, kod: 'IZ-X', durum: 'onay_bekliyor' })],
    );
    expect(harita.get('2026-07-21')?.[0]).toEqual({ tur: 'izin', etiket: 'IZ-2026-000001' });
    expect(harita.get('2026-07-22')).toHaveLength(1);
    expect(harita.get('2026-07-23')).toHaveLength(1);
    expect(harita.get('2026-07-24')).toBeUndefined();
    // Onaysız izin hiçbir güne yazılmaz.
    const tumEtiketler = [...harita.values()].flat().map((g) => g.etiket);
    expect(tumEtiketler).not.toContain('IZ-X');
  });

  it('aynı güne bakım + izin birlikte düşebilir', () => {
    const harita = takvimGirdileri(
      [plan({ sonraki_bakim_tarihi: '2026-07-21T09:00:00Z' })],
      [izin({})],
    );
    expect(harita.get('2026-07-21')).toHaveLength(2);
  });
});
