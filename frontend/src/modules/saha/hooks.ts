/**
 * Saha modülü veri hook'ları (TanStack Query) — cihaz listesi (sunucu-taraflı sayfalama).
 * Anahtarlar olayIsle.ts ile birebir aynıdır (canlı ``son_gorulme`` için invalidate edilir).
 */

import { useQuery } from '@tanstack/react-query';

import { istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Cihaz = components['schemas']['CihazCevapDTO'];
export type SahaOzet = components['schemas']['SahaOzetDTO'];

export const SAHA_ANAHTAR = {
  cihazlar: ['saha-cihazlar'] as const,
  ozet: ['saha-ozet'] as const,
};

export function useCihazlar(param: SayfaParam) {
  return useSayfaliSorgu<Cihaz>(SAHA_ANAHTAR.cihazlar, '/saha/cihazlar', param);
}

/** Saha cihaz KPI özeti (OzetSerit). */
export function useSahaOzet() {
  return useQuery({
    queryKey: SAHA_ANAHTAR.ozet,
    queryFn: () => istek<SahaOzet>('GET', `${PREFIX}/saha/ozet`),
  });
}
