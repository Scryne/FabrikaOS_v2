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
  it('uretim.eklendi → oee-ozet + uretim-verileri + saha-cihazlar + makine oee + KPI özetleri', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'uretim.eklendi', makine_id: 5 });
    expect(anahtarlar()).toContainEqual(['oee-ozet']);
    expect(anahtarlar()).toContainEqual(['uretim-verileri']);
    expect(anahtarlar()).toContainEqual(['saha-cihazlar']);
    expect(anahtarlar()).toContainEqual(['makine', 5, 'oee']);
    expect(anahtarlar()).toContainEqual(['uretim-ozet']);
    expect(anahtarlar()).toContainEqual(['saha-ozet']);
  });

  it('makine.durum → makineler + oee-ozet + makine detay + uretim-ozet', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'makine.durum', makine_id: 3, durum: 'calisiyor' });
    expect(anahtarlar()).toContainEqual(['makineler']);
    expect(anahtarlar()).toContainEqual(['oee-ozet']);
    expect(anahtarlar()).toContainEqual(['makine', 3]);
    expect(anahtarlar()).toContainEqual(['uretim-ozet']);
  });

  it('isemri.durum → is-emirleri + iş emri detay', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'isemri.durum', id: 9, durum: 'kapandi' });
    expect(anahtarlar()).toContainEqual(['is-emirleri']);
    expect(anahtarlar()).toContainEqual(['is-emri', 9]);
  });

  it('stok.kritik → malzeme + kritik + hareket + stok-ozet sorgularını invalidate eder', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'stok.kritik', malzeme_id: 3 });
    expect(anahtarlar()).toContainEqual(['malzemeler']);
    expect(anahtarlar()).toContainEqual(['stok-kritik']);
    expect(anahtarlar()).toContainEqual(['stok-hareketleri']);
    expect(anahtarlar()).toContainEqual(['stok-ozet']);
  });

  it('satinalma.durum → talep listesi + detayı + satinalma-ozet', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'satinalma.durum', id: 7 });
    expect(anahtarlar()).toContainEqual(['satinalma-talepleri']);
    expect(anahtarlar()).toContainEqual(['satinalma-talebi', 7]);
    expect(anahtarlar()).toContainEqual(['satinalma-ozet']);
  });

  it('kalite.kontrol → kalite kontrol listesi + kalite-ozet', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'kalite.kontrol', id: 4 });
    expect(anahtarlar()).toContainEqual(['kalite-kontrolleri']);
    expect(anahtarlar()).toContainEqual(['kalite-ozet']);
  });

  it('kalite.uygunsuzluk → uygunsuzluk listesi + detayı + kalite-ozet', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'kalite.uygunsuzluk', id: 8, durum: 'kok_neden' });
    expect(anahtarlar()).toContainEqual(['uygunsuzluklar']);
    expect(anahtarlar()).toContainEqual(['uygunsuzluk', 8]);
    expect(anahtarlar()).toContainEqual(['kalite-ozet']);
  });

  it('enerji.olcum → enerji ölçüm + trend + enerji-ozet sorgularını invalidate eder', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'enerji.olcum', makine_id: 2 });
    expect(anahtarlar()).toContainEqual(['enerji-tuketimleri']);
    expect(anahtarlar()).toContainEqual(['enerji-trend']);
    expect(anahtarlar()).toContainEqual(['enerji-ozet']);
  });

  it('isg.kaza / isg.risk / ik.izin → listeler + modül KPI özetleri', () => {
    const kaza = sahteQc();
    olayIsle(kaza.qc, { tur: 'isg.kaza', id: 1 });
    expect(kaza.anahtarlar()).toContainEqual(['is-kazalari']);
    expect(kaza.anahtarlar()).toContainEqual(['isg-ozet']);

    const risk = sahteQc();
    olayIsle(risk.qc, { tur: 'isg.risk', id: 2 });
    expect(risk.anahtarlar()).toContainEqual(['risk-degerlendirmeleri']);
    expect(risk.anahtarlar()).toContainEqual(['isg-ozet']);

    const izin = sahteQc();
    olayIsle(izin.qc, { tur: 'ik.izin', id: 3 });
    expect(izin.anahtarlar()).toContainEqual(['izin-talepleri']);
    expect(izin.anahtarlar()).toContainEqual(['izin-talebi', 3]);
    expect(izin.anahtarlar()).toContainEqual(['ik-ozet']);
  });

  it('sozlesme / talep / dys olayları modül KPI özetlerini de invalidate eder', () => {
    const soz = sahteQc();
    olayIsle(soz.qc, { tur: 'sozlesme.yaklasiyor', id: 4 });
    expect(soz.anahtarlar()).toContainEqual(['sozlesme-ozet']);

    const talep = sahteQc();
    olayIsle(talep.qc, { tur: 'talep.durum', id: 5 });
    expect(talep.anahtarlar()).toContainEqual(['talep-ozet']);

    const belge = sahteQc();
    olayIsle(belge.qc, { tur: 'dys.belge', id: 6 });
    expect(belge.anahtarlar()).toContainEqual(['dys-ozet']);
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

  it('rapor.hazir → rapor listesini invalidate eder', () => {
    const { qc, anahtarlar } = sahteQc();
    olayIsle(qc, { tur: 'rapor.hazir', id: 4, durum: 'hazir' });
    expect(anahtarlar()).toContainEqual(['raporlar']);
  });

  it('bilinmeyen olay türü hiçbir şeyi geçersizleştirmez', () => {
    const { qc, invalidateQueries } = sahteQc();
    olayIsle(qc, { tur: 'bilinmeyen.olay' });
    expect(invalidateQueries).not.toHaveBeenCalled();
  });
});
