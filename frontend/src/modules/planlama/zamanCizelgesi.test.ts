import { describe, expect, it } from 'vitest';

import { isDurumu, sureMetni, yerlestir, yukOrani, yukTonu } from './zamanCizelgesi';

const temel = {
  gecikme_dk: 0,
  sigmadi: false,
  kapasite_asimi: false,
  sira_kaynakli_gecikme: false,
};

describe('isDurumu', () => {
  it('öncelik sırası: sığmadı > kapasite aşımı > sıra gecikmesi > zamanında', () => {
    expect(isDurumu(temel)).toBe('zamaninda');
    expect(isDurumu({ ...temel, gecikme_dk: 30, sira_kaynakli_gecikme: true })).toBe(
      'sira_gecikmesi',
    );
    expect(isDurumu({ ...temel, gecikme_dk: 30, kapasite_asimi: true })).toBe('kapasite_asimi');
    expect(isDurumu({ ...temel, sigmadi: true, kapasite_asimi: true })).toBe('sigmadi');
  });
});

describe('yerlestir', () => {
  it('eksen içindeki parçayı yüzdeye çevirir', () => {
    expect(yerlestir(25, 50, 0, 100)).toEqual({ sol: 25, genislik: 25 });
  });
  it('taşan parçayı kırpar, dışarıdakini çizmez', () => {
    expect(yerlestir(-10, 20, 0, 100)).toEqual({ sol: 0, genislik: 20 });
    expect(yerlestir(90, 130, 0, 100)).toEqual({ sol: 90, genislik: 10 });
    expect(yerlestir(100, 120, 0, 100)).toBeNull();
    expect(yerlestir(-20, 0, 0, 100)).toBeNull();
    expect(yerlestir(10, 10, 0, 100)).toBeNull();
  });
  it('çok kısa parçaya en az genişlik verir, sağ kenarı aşmaz', () => {
    expect(yerlestir(10, 10.01, 0, 100)?.genislik).toBe(0.35);
    expect(yerlestir(99.9, 100, 0, 100)).toEqual({ sol: 99.9, genislik: 0.09999999999999432 });
  });
});

describe('sureMetni', () => {
  it('dakikayı okunur biçime çevirir', () => {
    expect(sureMetni(45)).toBe('45 dk');
    expect(sureMetni(60)).toBe('1 sa');
    expect(sureMetni(90)).toBe('1 sa 30 dk');
    expect(sureMetni(1440)).toBe('1 g');
    expect(sureMetni(1500)).toBe('1 g 1 sa');
  });
});

describe('yük', () => {
  it('oran ve ton', () => {
    expect(yukOrani(240, 480)).toBe(0.5);
    expect(yukOrani(10, 0)).toBeNull();
    expect(yukTonu(null)).toBe('yok');
    expect(yukTonu(0)).toBe('bos');
    expect(yukTonu(0.5)).toBe('normal');
    expect(yukTonu(0.9)).toBe('yogun');
    expect(yukTonu(1)).toBe('dolu');
    expect(yukTonu(1.4)).toBe('dolu');
  });
});
