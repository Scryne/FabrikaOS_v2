/**
 * Planlama veri hook'ları (S30, ADR-0049). Çizelge sunucuda her istekte yeniden hesaplanır;
 * plan girdisi değişince çizelge sorgusu geçersizleşir.
 */

import { useTranslation } from 'react-i18next';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { components } from '@/api/types.gen';

export type Cizelge = components['schemas']['CizelgeDTO'];
export type MakineCizelgesi = components['schemas']['MakineCizelgesiDTO'];
export type CizelgeIsi = components['schemas']['CizelgeIsiDTO'];
export type PlanGirdisi = components['schemas']['PlanGirdisiDTO'];

export type CizelgeParam = { baslangic: string; gun: number; makineId?: number };

export const PLANLAMA_ANAHTAR = {
  cizelge: ['planlama-cizelge'] as const,
};

export function useCizelge(p: CizelgeParam) {
  const q = new URLSearchParams({ baslangic: p.baslangic, gun: String(p.gun) });
  if (p.makineId) q.set('makine_id', String(p.makineId));
  return useQuery({
    queryKey: [...PLANLAMA_ANAHTAR.cizelge, p.baslangic, p.gun, p.makineId ?? null],
    queryFn: () => istek<Cizelge>('GET', `${PREFIX}/planlama/cizelge?${q.toString()}`),
    placeholderData: keepPreviousData,
    // "Şimdi" çizgisi ve devam eden işler kayar: dakikada bir tazele.
    refetchInterval: 60_000,
  });
}

export function usePlanGirdisi() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: ({ isEmriId, govde }: { isEmriId: number; govde: PlanGirdisi }) =>
      istek<unknown>('PUT', `${PREFIX}/is-emirleri/${isEmriId}/plan`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: PLANLAMA_ANAHTAR.cizelge });
      message.success(t('planlama.kaydedildi'));
    },
    onError: (hata: unknown) =>
      message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik')),
  });
}
