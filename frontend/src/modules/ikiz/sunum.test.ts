import { describe, expect, it } from 'vitest';

import {
  bosKonum,
  durumRengi,
  kioskKarolari,
  konumdanYuzde,
  oeeEtiket,
  svgKonum,
  taslakDugumler,
  yuzdeKirp,
} from './sunum';

describe('ikiz sunum', () => {
  it('yuzdeKirp sınırlar ve 0.1 hassasiyetine yuvarlar', () => {
    expect(yuzdeKirp(-5)).toBe(0);
    expect(yuzdeKirp(101)).toBe(100);
    expect(yuzdeKirp(33.333)).toBe(33.3);
    expect(yuzdeKirp(66.66)).toBe(66.7);
  });

  it('konumdanYuzde pointer konumunu yüzdeye çevirir (kırpılmış)', () => {
    const kutu = { left: 100, top: 50, width: 800, height: 450 };
    expect(konumdanYuzde(500, 275, kutu)).toEqual({ x: 50, y: 50 });
    expect(konumdanYuzde(100, 50, kutu)).toEqual({ x: 0, y: 0 });
    // Tuval dışı → kırpılır.
    expect(konumdanYuzde(1000, 600, kutu)).toEqual({ x: 100, y: 100 });
    // Bozuk kutu → güvenli sıfır.
    expect(konumdanYuzde(10, 10, { left: 0, top: 0, width: 0, height: 0 })).toEqual({
      x: 0,
      y: 0,
    });
  });

  it('svgKonum yüzdeyi 160×90 viewBox koordinatına ölçekler', () => {
    expect(svgKonum(0, 0)).toEqual({ sx: 0, sy: 0 });
    expect(svgKonum(50, 50)).toEqual({ sx: 80, sy: 45 });
    expect(svgKonum(100, 100)).toEqual({ sx: 160, sy: 90 });
  });

  it('durumRengi bilinen durumları eşler, bilinmeyene soluk döner', () => {
    expect(durumRengi('calisiyor')).toBe('var(--basari)');
    expect(durumRengi('ariza')).toBe('var(--hata)');
    expect(durumRengi('bilinmeyen')).toBe('var(--metin-soluk)');
  });

  it('oeeEtiket yüzde biçimler, veri yoksa tire', () => {
    expect(oeeEtiket(0.876)).toBe('%88');
    expect(oeeEtiket(null)).toBe('—');
    expect(oeeEtiket(undefined)).toBe('—');
  });

  it('taslakDugumler durum düğümlerini PUT gövdesine indirger', () => {
    const taslak = taslakDugumler([
      {
        makine_id: 3,
        makine_kod: 'M-1',
        makine_ad: 'Pres',
        durum: 'calisiyor',
        x: 10,
        y: 20,
        bolge: 'Hat A',
        oee: 0.9,
        toplam_adet: 5,
        son_veri_zamani: null,
      },
    ]);
    expect(taslak).toEqual([{ makine_id: 3, x: 10, y: 20, bolge: 'Hat A' }]);
  });

  it('bosKonum mevcut düğümlerle çakışmayan konum önerir', () => {
    expect(bosKonum([])).toEqual({ x: 15, y: 18 });
    // İlk aday doluysa bir sonraki ızgara hücresine kayar.
    const oneri = bosKonum([{ x: 15, y: 18 }]);
    expect(oneri).toEqual({ x: 26, y: 18 });
    // Önerilen konum hiçbir düğümün ±11/±12 komşuluğunda değildir.
    const dolu = [
      { x: 15, y: 18 },
      { x: 26, y: 18 },
      { x: 55, y: 30 },
    ];
    const yeni = bosKonum(dolu);
    expect(dolu.some((d) => Math.abs(d.x - yeni.x) < 11 && Math.abs(d.y - yeni.y) < 12)).toBe(
      false,
    );
  });

  it('kioskKarolari düğümler + yerleşmemişleri kod sırasıyla birleştirir', () => {
    const karolar = kioskKarolari({
      dugumler: [
        {
          makine_id: 2,
          makine_kod: 'M-2',
          makine_ad: 'Kaynak',
          durum: 'ariza',
          x: 5,
          y: 5,
          bolge: '',
          oee: 0.7,
          toplam_adet: 100,
          son_veri_zamani: null,
        },
      ],
      yerlesmemis: [{ makine_id: 1, makine_kod: 'M-1', makine_ad: 'Pres', durum: 'durdu' }],
    });
    expect(karolar.map((k) => k.kod)).toEqual(['M-1', 'M-2']);
    expect(karolar[0]).toMatchObject({ oee: null, toplam_adet: 0, durum: 'durdu' });
    expect(karolar[1]).toMatchObject({ oee: 0.7, toplam_adet: 100 });
  });
});
