/**
 * Duyuru veri hook'ları (TanStack Query). Anahtarlar olayIsle.ts ile birebir aynıdır.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Duyuru = components['schemas']['DuyuruCevapDTO'];
export type DuyuruOlustur = components['schemas']['DuyuruOlusturDTO'];

export const DUYURU_ANAHTAR = {
  liste: ['duyurular'] as const,
  detay: (id: number) => ['duyuru', id] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useDuyurular(param: SayfaParam) {
  return useSayfaliSorgu<Duyuru>(DUYURU_ANAHTAR.liste, '/duyurular', param);
}

export function useDuyuru(id: number) {
  return useQuery({
    queryKey: DUYURU_ANAHTAR.detay(id),
    queryFn: () => istek<Duyuru>('GET', `${PREFIX}/duyurular/${id}`),
    enabled: id > 0,
  });
}

export function useDuyuruOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: DuyuruOlustur) => istek<Duyuru>('POST', `${PREFIX}/duyurular`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DUYURU_ANAHTAR.liste });
      message.success(t('duyuru.olusturuldu'));
    },
    onError: hataGoster,
  });
}

/** Yayın aksiyonu: yayinla | kaldir. */
export function useDuyuruYayin() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, aksiyon }: { id: number; aksiyon: 'yayinla' | 'kaldir' }) =>
      istek<Duyuru>('POST', `${PREFIX}/duyurular/${id}/${aksiyon}`),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: DUYURU_ANAHTAR.liste });
      void qc.invalidateQueries({ queryKey: DUYURU_ANAHTAR.detay(id) });
      message.success(t('duyuru.durum_guncellendi'));
    },
    onError: hataGoster,
  });
}
