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

  it('bilinmeyen olay türü hiçbir şeyi geçersizleştirmez', () => {
    const { qc, invalidateQueries } = sahteQc();
    olayIsle(qc, { tur: 'bilinmeyen.olay' });
    expect(invalidateQueries).not.toHaveBeenCalled();
  });
});
