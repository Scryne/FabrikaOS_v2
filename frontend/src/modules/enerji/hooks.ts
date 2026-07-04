/** Enerji veri hook'ları (TanStack Query). Trend anahtarı filtreye göre ayrışır. */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type EnerjiOlcum = components['schemas']['EnerjiOlcumCevapDTO'];
export type EnerjiOlcumOlustur = components['schemas']['EnerjiOlcumOlusturDTO'];
export type TrendNokta = components['schemas']['EnerjiTrendNoktaDTO'];

export const ENERJI_ANAHTAR = {
  olcumler: ['enerji-tuketimleri'] as const,
  trend: ['enerji-trend'] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useEnerjiOlcumler(param: SayfaParam) {
  return useSayfaliSorgu<EnerjiOlcum>(ENERJI_ANAHTAR.olcumler, '/enerji-tuketimleri', param);
}

export function useOlcumEkle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: EnerjiOlcumOlustur) =>
      istek<EnerjiOlcum>('POST', `${PREFIX}/enerji-tuketimleri`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ENERJI_ANAHTAR.olcumler });
      void qc.invalidateQueries({ queryKey: ENERJI_ANAHTAR.trend });
      message.success(t('enerji.olcum_eklendi'));
    },
    onError: hataGoster,
  });
}

export function useEnerjiTrend(sorgu: {
  enerji_turu?: string;
  makine_id?: number;
  aralik: string;
  baslangic?: string;
  bitis?: string;
}) {
  const params = new URLSearchParams();
  if (sorgu.enerji_turu) params.set('enerji_turu', sorgu.enerji_turu);
  if (sorgu.makine_id) params.set('makine_id', String(sorgu.makine_id));
  params.set('aralik', sorgu.aralik);
  if (sorgu.baslangic) params.set('baslangic', sorgu.baslangic);
  if (sorgu.bitis) params.set('bitis', sorgu.bitis);
  const qs = params.toString();
  return useQuery({
    queryKey: [...ENERJI_ANAHTAR.trend, qs],
    queryFn: () => istek<TrendNokta[]>('GET', `${PREFIX}/enerji-tuketimleri/trend?${qs}`),
  });
}
