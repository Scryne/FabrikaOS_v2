import { describe, expect, it } from 'vitest';

import { durumRengi, konumdanYuzde, oeeEtiket, svgKonum, taslakDugumler, yuzdeKirp } from './sunum';

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
});
