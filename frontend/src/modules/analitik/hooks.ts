/** Analitik veri hook'ları (TanStack Query) — modüller-arası KPI özeti + günlük üretim trendi. */

import { useQuery } from '@tanstack/react-query';

import { istek, PREFIX } from '@/api/client';
import type { components } from '@/api/types.gen';

export type KpiCevap = components['schemas']['KpiCevapDTO'];
export type TrendNoktasi = components['schemas']['TrendNoktasiDTO'];

export function useKpi(gun: number) {
  return useQuery({
    queryKey: ['analitik-kpi', gun],
    queryFn: () => istek<KpiCevap>('GET', `${PREFIX}/analitik/kpi?gun=${gun}`),
  });
}

export function useTrend(gun: number) {
  return useQuery({
    queryKey: ['analitik-trend', gun],
    queryFn: () => istek<TrendNoktasi[]>('GET', `${PREFIX}/analitik/trend?gun=${gun}`),
  });
}
