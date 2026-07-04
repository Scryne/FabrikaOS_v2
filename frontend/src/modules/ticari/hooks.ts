/** Ticari özet (pano) hook'u — CRM/sözleşme/talep/duyuru sayaçları + listeler. */

import { useQuery } from '@tanstack/react-query';

import { istek, PREFIX } from '@/api/client';
import type { components } from '@/api/types.gen';

export type TicariOzet = components['schemas']['TicariOzetDTO'];

export function useTicariOzet() {
  return useQuery({
    queryKey: ['ticari-ozet'],
    queryFn: () => istek<TicariOzet>('GET', `${PREFIX}/ticari/ozet`),
  });
}
