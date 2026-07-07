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
    case 'kalite.kontrol':
      void qc.invalidateQueries({ queryKey: ['kalite-kontrolleri'] });
      break;
    case 'kalite.uygunsuzluk': {
      void qc.invalidateQueries({ queryKey: ['uygunsuzluklar'] });
      const uygunsuzlukId = typeof olay.id === 'number' ? olay.id : undefined;
      if (uygunsuzlukId !== undefined)
        void qc.invalidateQueries({ queryKey: ['uygunsuzluk', uygunsuzlukId] });
      break;
    }
    case 'enerji.olcum':
      void qc.invalidateQueries({ queryKey: ['enerji-tuketimleri'] });
      void qc.invalidateQueries({ queryKey: ['enerji-trend'] });
      break;
    case 'isg.kaza':
      void qc.invalidateQueries({ queryKey: ['is-kazalari'] });
      break;
    case 'isg.risk':
      void qc.invalidateQueries({ queryKey: ['risk-degerlendirmeleri'] });
      break;
    case 'ik.izin': {
      void qc.invalidateQueries({ queryKey: ['izin-talepleri'] });
      const izinId = typeof olay.id === 'number' ? olay.id : undefined;
      if (izinId !== undefined) void qc.invalidateQueries({ queryKey: ['izin-talebi', izinId] });
      break;
    }
    case 'crm.firma':
      void qc.invalidateQueries({ queryKey: ['firmalar'] });
      break;
    case 'sozlesme.durum':
    case 'sozlesme.yaklasiyor': {
      void qc.invalidateQueries({ queryKey: ['sozlesmeler'] });
      void qc.invalidateQueries({ queryKey: ['sozlesme-yaklasan'] });
      void qc.invalidateQueries({ queryKey: ['ticari-ozet'] });
      const sozId = typeof olay.id === 'number' ? olay.id : undefined;
      if (sozId !== undefined) void qc.invalidateQueries({ queryKey: ['sozlesme', sozId] });
      break;
    }
    case 'talep.olusturuldu':
    case 'talep.durum': {
      void qc.invalidateQueries({ queryKey: ['talepler'] });
      void qc.invalidateQueries({ queryKey: ['ticari-ozet'] });
      const talepId = typeof olay.id === 'number' ? olay.id : undefined;
      if (talepId !== undefined) void qc.invalidateQueries({ queryKey: ['talep', talepId] });
      break;
    }
    case 'dys.belge': {
      void qc.invalidateQueries({ queryKey: ['belgeler'] });
      const belgeId = typeof olay.id === 'number' ? olay.id : undefined;
      if (belgeId !== undefined) {
        void qc.invalidateQueries({ queryKey: ['belge', belgeId] });
        void qc.invalidateQueries({ queryKey: ['belge-surumleri', belgeId] });
      }
      break;
    }
    case 'duyuru.yeni':
      void qc.invalidateQueries({ queryKey: ['duyurular'] });
      void qc.invalidateQueries({ queryKey: ['ticari-ozet'] });
      break;
    case 'ai.model':
      // Eğitim bitti/başarısız → kart durumu + (yeni aktif sürümle) tüm tahminler tazelensin.
      void qc.invalidateQueries({ queryKey: ['ai-modeller'] });
      void qc.invalidateQueries({ queryKey: ['ai-tahmin'] });
      break;
    case 'anomali.tespit':
      void qc.invalidateQueries({ queryKey: ['ai-tahmin', 'anomali'] });
      break;
    default:
      break;
  }
}
