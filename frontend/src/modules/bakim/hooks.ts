/** Bakım modülü veri hook'ları (TanStack Query) — plan listesi + oluştur/güncelle mutasyonları. */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type BakimPlani = components['schemas']['BakimPlaniCevapDTO'];
export type BakimPlaniOlustur = components['schemas']['BakimPlaniOlusturDTO'];
export type BakimPlaniGuncelle = components['schemas']['BakimPlaniGuncelleDTO'];
export type BakimOzet = components['schemas']['BakimOzetDTO'];

export const BAKIM_ANAHTAR = {
  planlar: ['bakim-planlari'] as const,
  ozet: ['bakim-ozet'] as const,
};

/** Bakım KPI özeti (OzetSerit). */
export function useBakimOzet() {
  return useQuery({
    queryKey: BAKIM_ANAHTAR.ozet,
    queryFn: () => istek<BakimOzet>('GET', `${PREFIX}/bakim/ozet`),
  });
}

/** Backend beyaz-listesiyle birebir (``BAKIM_TIPLERI``). */
export const BAKIM_TIPLERI = ['onleyici', 'kestirimci', 'periyodik'];

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useBakimPlanlari(param: SayfaParam) {
  return useSayfaliSorgu<BakimPlani>(BAKIM_ANAHTAR.planlar, '/bakim-planlari', param);
}

export function useBakimPlaniOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: BakimPlaniOlustur) =>
      istek<BakimPlani>('POST', `${PREFIX}/bakim-planlari`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: BAKIM_ANAHTAR.planlar });
      void qc.invalidateQueries({ queryKey: BAKIM_ANAHTAR.ozet });
      message.success(t('bakim.olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useBakimPlaniGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: BakimPlaniGuncelle }) =>
      istek<BakimPlani>('PATCH', `${PREFIX}/bakim-planlari/${id}`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: BAKIM_ANAHTAR.planlar });
      void qc.invalidateQueries({ queryKey: BAKIM_ANAHTAR.ozet });
      message.success(t('bakim.guncellendi'));
    },
    onError: hataGoster,
  });
}
