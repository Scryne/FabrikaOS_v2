/**
 * Rapor veri hook'ları (TanStack Query) — liste (üretim sürerken yoklamalı) + oluştur + indir.
 *
 * Üretim arka planda sürerken (`kuyrukta`/`hazirlaniyor`) liste 4 sn'de bir yoklanır;
 * `rapor.hazir` gerçek-zaman olayı kaçarsa da durum tazelenir (S13 `useModeller` deseni).
 */

import { useTranslation } from 'react-i18next';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, istekIndir, istekSayfali, PREFIX } from '@/api/client';
import { type SayfaParam, sorguDizesi } from '@/api/sayfalama';

import type { Rapor, RaporOlustur } from './sunum';

export function useRaporlar(param: SayfaParam) {
  return useQuery({
    queryKey: ['raporlar', param],
    queryFn: () => istekSayfali<Rapor>(`${PREFIX}/raporlar?${sorguDizesi(param)}`),
    placeholderData: keepPreviousData,
    refetchInterval: (sorgu) =>
      sorgu.state.data?.veri.some((r) => r.durum === 'kuyrukta' || r.durum === 'hazirlaniyor')
        ? 4000
        : false,
  });
}

export function useRaporOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: (govde: RaporOlustur) => istek<Rapor>('POST', `${PREFIX}/raporlar`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['raporlar'] });
      message.success(t('rapor.uretim_baslatildi'));
    },
    onError: (hata) =>
      message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik')),
  });
}

/** Hazır raporu indirir ve tarayıcıda kaydettirir. */
export async function raporuIndir(raporId: number, yedekAd: string): Promise<void> {
  const { blob, dosyaAdi } = await istekIndir(`${PREFIX}/raporlar/${raporId}/indir`);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = dosyaAdi ?? yedekAd;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
