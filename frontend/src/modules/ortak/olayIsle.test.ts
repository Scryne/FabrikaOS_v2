import { describe, expect, it, vi } from 'vitest';
import type { QueryClient } from '@tanstack/react-query';

import { olayIsle } from './olayIsle';

function sahteQc() {
  const invalidateQueries = vi.fn();
  return {
    qc: { invalidateQueries } as unknown as QueryClient,
    anahtarlar: () => invalidateQueries.mock.calls.map((c) => c[0].queryKey),
    invalidateQueries,
  };
}

describe('olayIsle (gerçek-zaman olay → query invalidation)', () => {
  it('uretim.eklendi → oee-ozet + uretim-verileri + saha-cihazlar + makine oee', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'uretim.eklendi', makine_id: 5 });
    expect(anahtarlar()).toContainEqual(['oee-ozet']);
    expect(anahtarlar()).toContainEqual(['uretim-verileri']);
    expect(anahtarlar()).toContainEqual(['saha-cihazlar']);
    expect(anahtarlar()).toContainEqual(['makine', 5, 'oee']);
  });

  it('makine.durum → makineler + oee-ozet + makine detay', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'makine.durum', makine_id: 3, durum: 'calisiyor' });
    expect(anahtarlar()).toContainEqual(['makineler']);
    expect(anahtarlar()).toContainEqual(['oee-ozet']);
    expect(anahtarlar()).toContainEqual(['makine', 3]);
  });

  it('isemri.durum → is-emirleri + iş emri detay', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'isemri.durum', id: 9, durum: 'kapandi' });
    expect(anahtarlar()).toContainEqual(['is-emirleri']);
    expect(anahtarlar()).toContainEqual(['is-emri', 9]);
  });

  it('stok.kritik → malzeme + kritik + hareket sorgularını invalidate eder', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'stok.kritik', malzeme_id: 3 });
    expect(anahtarlar()).toContainEqual(['malzemeler']);
    expect(anahtarlar()).toContainEqual(['stok-kritik']);
    expect(anahtarlar()).toContainEqual(['stok-hareketleri']);
  });

  it('satinalma.durum → talep listesi + detayını invalidate eder', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'satinalma.durum', id: 7 });
    expect(anahtarlar()).toContainEqual(['satinalma-talepleri']);
    expect(anahtarlar()).toContainEqual(['satinalma-talebi', 7]);
  });

  it('kalite.kontrol → kalite kontrol listesini invalidate eder', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'kalite.kontrol', id: 4 });
    expect(anahtarlar()).toContainEqual(['kalite-kontrolleri']);
  });

  it('kalite.uygunsuzluk → uygunsuzluk listesi + detayını invalidate eder', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'kalite.uygunsuzluk', id: 8, durum: 'kok_neden' });
    expect(anahtarlar()).toContainEqual(['uygunsuzluklar']);
    expect(anahtarlar()).toContainEqual(['uygunsuzluk', 8]);
  });

  it('enerji.olcum → enerji ölçüm + trend sorgularını invalidate eder', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'enerji.olcum', makine_id: 2 });
    expect(anahtarlar()).toContainEqual(['enerji-tuketimleri']);
    expect(anahtarlar()).toContainEqual(['enerji-trend']);
  });

  it('ai.model → model kayıtları + tüm tahmin sorgularını invalidate eder', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'ai.model', id: 3, model_turu: 'oee', durum: 'hazir' });
    expect(anahtarlar()).toContainEqual(['ai-modeller']);
    expect(anahtarlar()).toContainEqual(['ai-tahmin']);
  });

  it('anomali.tespit → anomali tahmin sorgusunu invalidate eder', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'anomali.tespit', id: 12 });
    expect(anahtarlar()).toContainEqual(['ai-tahmin', 'anomali']);
  });

  it('bilinmeyen olay türü hiçbir şeyi geçersizleştirmez', () => {
    const { qc, invalidateQueries } = sahteQc();
    olayIsle(qc, { tur: 'bilinmeyen.olay' });
    expect(invalidateQueries).not.toHaveBeenCalled();
  });
});
