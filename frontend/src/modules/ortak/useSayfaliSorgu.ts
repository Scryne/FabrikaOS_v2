/**
 * Sayfalı liste sorgusu için genel TanStack Query hook'u.
 *
 * ``istekSayfali`` ile ``{ veri, meta }`` döndürür; sayfa değişiminde önceki veriyi korur
 * (``keepPreviousData``) → tablo titremeden geçiş yapar.
 */

import { keepPreviousData, useQuery } from '@tanstack/react-query';

import { istekSayfali, PREFIX, type SayfaMeta } from '@/api/client';
import { type SayfaParam, sorguDizesi } from '@/api/sayfalama';

export type SayfaliSonuc<T> = { veri: T[]; meta: SayfaMeta };

export function useSayfaliSorgu<T>(anahtar: readonly unknown[], yol: string, param: SayfaParam) {
  return useQuery<SayfaliSonuc<T>>({
    queryKey: [...anahtar, param],
    queryFn: () => istekSayfali<T>(`${PREFIX}${yol}?${sorguDizesi(param)}`),
    placeholderData: keepPreviousData,
  });
}
