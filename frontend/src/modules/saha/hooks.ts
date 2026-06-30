/**
 * Saha modülü veri hook'ları (TanStack Query) — cihaz listesi (sunucu-taraflı sayfalama).
 * Anahtarlar olayIsle.ts ile birebir aynıdır (canlı ``son_gorulme`` için invalidate edilir).
 */

import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Cihaz = components['schemas']['CihazCevapDTO'];

export const SAHA_ANAHTAR = {
  cihazlar: ['saha-cihazlar'] as const,
};

export function useCihazlar(param: SayfaParam) {
  return useSayfaliSorgu<Cihaz>(SAHA_ANAHTAR.cihazlar, '/saha/cihazlar', param);
}
