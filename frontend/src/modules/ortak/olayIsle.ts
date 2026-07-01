/**
 * Gerçek-zaman olayını ilgili TanStack Query anahtarlarını geçersizleştirerek işler.
 *
 * Olay yalnız bir **sinyaldir** (kimlik/ids taşır, veri değil); ilgili sorgular invalidate
 * edilince güncel veri yeniden çekilir. Anahtarlar modül hook'larındakilerle birebir aynıdır.
 */

import type { QueryClient } from '@tanstack/react-query';

import type { Olay } from '@/api/gercekzaman';

export function olayIsle(qc: QueryClient, olay: Olay): void {
  const makineId = typeof olay.makine_id === 'number' ? olay.makine_id : undefined;
  const isEmriId = typeof olay.id === 'number' ? olay.id : undefined;

  switch (olay.tur) {
    case 'uretim.eklendi':
      void qc.invalidateQueries({ queryKey: ['oee-ozet'] });
      void qc.invalidateQueries({ queryKey: ['uretim-verileri'] });
      // Saha ölçümü cihazın son_gorulme'sini günceller → liste canlı yansısın.
      void qc.invalidateQueries({ queryKey: ['saha-cihazlar'] });
      if (makineId !== undefined)
        void qc.invalidateQueries({ queryKey: ['makine', makineId, 'oee'] });
      break;
    case 'makine.durum':
      void qc.invalidateQueries({ queryKey: ['makineler'] });
      void qc.invalidateQueries({ queryKey: ['oee-ozet'] });
      if (makineId !== undefined) void qc.invalidateQueries({ queryKey: ['makine', makineId] });
      break;
    case 'isemri.durum':
    case 'isemri.olusturuldu':
      void qc.invalidateQueries({ queryKey: ['is-emirleri'] });
      if (isEmriId !== undefined) void qc.invalidateQueries({ queryKey: ['is-emri', isEmriId] });
      break;
    case 'stok.hareket':
    case 'stok.kritik':
      void qc.invalidateQueries({ queryKey: ['malzemeler'] });
      void qc.invalidateQueries({ queryKey: ['stok-kritik'] });
      void qc.invalidateQueries({ queryKey: ['stok-hareketleri'] });
      break;
    case 'satinalma.durum': {
      void qc.invalidateQueries({ queryKey: ['satinalma-talepleri'] });
      const talepId = typeof olay.id === 'number' ? olay.id : undefined;
      if (talepId !== undefined)
        void qc.invalidateQueries({ queryKey: ['satinalma-talebi', talepId] });
      break;
    }
    default:
      break;
  }
}
