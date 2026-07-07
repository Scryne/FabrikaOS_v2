import { describe, expect, it } from 'vitest';

import { kalanGunRenk, type ModelKaydi, MODEL_TURLERI, sonModeller, TAHMIN_YOLU } from './sunum';

function kayit(id: number, tur: string, durum = 'hazir', aktif = true): ModelKaydi {
  return {
    id,
    tur,
    surum: id,
    durum,
    aktif,
    hata: '',
    olusturma_tarihi: '2026-07-07T10:00:00Z',
  } as ModelKaydi;
}

describe('AI sunum yardımcıları', () => {
  it('tahmin yolu eşlemesi backend uçlarını aynalar', () => {
    expect(TAHMIN_YOLU.kestirimci_bakim).toBe('kestirimci-bakim');
    expect(MODEL_TURLERI).toContain('anomali');
    for (const tur of MODEL_TURLERI) expect(TAHMIN_YOLU[tur]).toBeTruthy();
  });

  it('sonModeller: tür başına ilk (en yeni) kaydı seçer', () => {
    // liste id azalan gelir → 5 numaralı oee kaydı 2'den önce görülür
    const liste = [kayit(5, 'oee', 'egitiliyor', false), kayit(3, 'stok'), kayit(2, 'oee')];
    const sonlar = sonModeller(liste);
    expect(sonlar.oee?.id).toBe(5);
    expect(sonlar.oee?.durum).toBe('egitiliyor');
    expect(sonlar.stok?.id).toBe(3);
    expect(sonlar.kestirimci_bakim).toBeUndefined();
  });

  it('kalanGunRenk aciliyet eşikleri', () => {
    expect(kalanGunRenk(3)).toBe('error');
    expect(kalanGunRenk(7)).toBe('error');
    expect(kalanGunRenk(10)).toBe('warning');
    expect(kalanGunRenk(30)).toBe('success');
  });
});
