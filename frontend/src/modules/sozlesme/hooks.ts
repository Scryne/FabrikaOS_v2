/**
 * Sözleşme veri hook'ları (TanStack Query). Anahtarlar olayIsle.ts ile birebir aynıdır.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Sozlesme = components['schemas']['SozlesmeCevapDTO'];
export type SozlesmeOlustur = components['schemas']['SozlesmeOlusturDTO'];
export type SozlesmeGuncelle = components['schemas']['SozlesmeGuncelleDTO'];

export const SOZLESME_ANAHTAR = {
  liste: ['sozlesmeler'] as const,
  detay: (id: number) => ['sozlesme', id] as const,
  yaklasan: ['sozlesme-yaklasan'] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useSozlesmeler(param: SayfaParam) {
  return useSayfaliSorgu<Sozlesme>(SOZLESME_ANAHTAR.liste, '/sozlesmeler', param);
}

export function useSozlesme(id: number) {
  return useQuery({
    queryKey: SOZLESME_ANAHTAR.detay(id),
    queryFn: () => istek<Sozlesme>('GET', `${PREFIX}/sozlesmeler/${id}`),
    enabled: id > 0,
  });
}

export function useYaklasanSozlesmeler() {
  return useQuery({
    queryKey: SOZLESME_ANAHTAR.yaklasan,
    queryFn: () => istek<Sozlesme[]>('GET', `${PREFIX}/sozlesmeler/yaklasan`),
  });
}

export function useSozlesmeOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: SozlesmeOlustur) => istek<Sozlesme>('POST', `${PREFIX}/sozlesmeler`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SOZLESME_ANAHTAR.liste });
      message.success(t('sozlesme.olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useSozlesmeGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: SozlesmeGuncelle }) =>
      istek<Sozlesme>('PATCH', `${PREFIX}/sozlesmeler/${id}`, govde),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: SOZLESME_ANAHTAR.liste });
      void qc.invalidateQueries({ queryKey: SOZLESME_ANAHTAR.detay(id) });
      message.success(t('sozlesme.guncellendi'));
    },
    onError: hataGoster,
  });
}

export function useSozlesmeDurum() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, durum }: { id: number; durum: string }) =>
      istek<Sozlesme>('PATCH', `${PREFIX}/sozlesmeler/${id}/durum`, { durum }),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: SOZLESME_ANAHTAR.liste });
      void qc.invalidateQueries({ queryKey: SOZLESME_ANAHTAR.detay(id) });
      void qc.invalidateQueries({ queryKey: SOZLESME_ANAHTAR.yaklasan });
      message.success(t('sozlesme.durum_guncellendi'));
    },
    onError: hataGoster,
  });
}
