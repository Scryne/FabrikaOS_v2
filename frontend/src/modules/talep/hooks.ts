/**
 * Talep veri hook'ları (TanStack Query). Anahtarlar olayIsle.ts ile birebir aynıdır.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Talep = components['schemas']['TalepCevapDTO'];
export type TalepOlustur = components['schemas']['TalepOlusturDTO'];
export type TalepGuncelle = components['schemas']['TalepGuncelleDTO'];
export type TalepOzet = components['schemas']['TalepOzetDTO'];

export const TALEP_ANAHTAR = {
  liste: ['talepler'] as const,
  pano: ['talepler', 'pano'] as const,
  detay: (id: number) => ['talep', id] as const,
  ozet: ['talep-ozet'] as const,
};

/** Talep KPI özeti (OzetSerit + board sayaçları). */
export function useTalepOzet() {
  return useQuery({
    queryKey: TALEP_ANAHTAR.ozet,
    queryFn: () => istek<TalepOzet>('GET', `${PREFIX}/talep/ozet`),
  });
}

/** Board için tek çekim (istemcide gruplama): en güncel 100 talep. */
export function useTalepPano() {
  return useQuery({
    queryKey: TALEP_ANAHTAR.pano,
    queryFn: () =>
      istek<Talep[]>('GET', `${PREFIX}/talepler?sayfa=1&adet=100&siralama=id&yon=desc`),
  });
}

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useTalepler(param: SayfaParam) {
  return useSayfaliSorgu<Talep>(TALEP_ANAHTAR.liste, '/talepler', param);
}

export function useTalep(id: number) {
  return useQuery({
    queryKey: TALEP_ANAHTAR.detay(id),
    queryFn: () => istek<Talep>('GET', `${PREFIX}/talepler/${id}`),
    enabled: id > 0,
  });
}

export function useTalepOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: TalepOlustur) => istek<Talep>('POST', `${PREFIX}/talepler`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TALEP_ANAHTAR.liste });
      void qc.invalidateQueries({ queryKey: TALEP_ANAHTAR.ozet });
      message.success(t('talep.olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useTalepGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: TalepGuncelle }) =>
      istek<Talep>('PATCH', `${PREFIX}/talepler/${id}`, govde),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: TALEP_ANAHTAR.liste });
      void qc.invalidateQueries({ queryKey: TALEP_ANAHTAR.detay(id) });
      void qc.invalidateQueries({ queryKey: TALEP_ANAHTAR.ozet });
      message.success(t('talep.guncellendi'));
    },
    onError: hataGoster,
  });
}

export function useTalepDurum() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, durum }: { id: number; durum: string }) =>
      istek<Talep>('PATCH', `${PREFIX}/talepler/${id}/durum`, { durum }),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: TALEP_ANAHTAR.liste });
      void qc.invalidateQueries({ queryKey: TALEP_ANAHTAR.detay(id) });
      void qc.invalidateQueries({ queryKey: TALEP_ANAHTAR.ozet });
      message.success(t('talep.durum_guncellendi'));
    },
    onError: hataGoster,
  });
}
