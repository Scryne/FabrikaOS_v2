/**
 * Rapor modülü saf sunum yardımcıları — tür/biçim beyaz-listeleri + durum rozet eşlemesi.
 *
 * Backend `modules/rapor/birimler.py` beyaz-listesinin aynasıdır.
 */

import type { components } from '@/api/types.gen';

export type Rapor = components['schemas']['RaporCevapDTO'];
export type RaporOlustur = components['schemas']['RaporOlusturDTO'];

export const RAPOR_TURLERI = ['uretim', 'stok', 'kalite', 'enerji', 'isemri'] as const;
export type RaporTuru = (typeof RAPOR_TURLERI)[number];

export const RAPOR_BICIMLERI = ['pdf', 'xlsx'] as const;
export type RaporBicimi = (typeof RAPOR_BICIMLERI)[number];

/** Rapor durumu → antd Tag rengi (yaşam döngüsü: kuyrukta→hazirlaniyor→hazir|basarisiz). */
export const DURUM_RENK: Record<string, string> = {
  kuyrukta: 'default',
  hazirlaniyor: 'processing',
  hazir: 'success',
  basarisiz: 'error',
};

/** Rapor yalnız `hazir` durumda indirilebilir (aksi backend'de 409). */
export function indirilebilir(durum: string): boolean {
  return durum === 'hazir';
}

/** Bayt boyutunu insan-okur biçime çevirir (KB/MB, tr-TR ondalık). */
export function boyutMetni(bayt: number): string {
  if (bayt <= 0) return '—';
  if (bayt < 1024) return `${bayt} B`;
  if (bayt < 1024 * 1024)
    return `${(bayt / 1024).toLocaleString('tr-TR', { maximumFractionDigits: 1 })} KB`;
  return `${(bayt / (1024 * 1024)).toLocaleString('tr-TR', { maximumFractionDigits: 1 })} MB`;
}
