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
export type MtbfMttr = components['schemas']['MtbfMttrCevapDTO'];
export type VadeTarama = components['schemas']['VadeTaramaCevapDTO'];

export const BAKIM_ANAHTAR = {
  planlar: ['bakim-planlari'] as const,
  ozet: ['bakim-ozet'] as const,
  metrikler: (makineId: number, gun: number) => ['bakim-metrikler', makineId, gun] as const,
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

/** Makine güvenilirlik metrikleri (S24) — MTBF/MTTR; arıza yoksa metrikler null. */
export function useBakimMetrikleri(makineId: number, gun = 90, etkin = true) {
  return useQuery({
    queryKey: BAKIM_ANAHTAR.metrikler(makineId, gun),
    queryFn: () =>
      istek<MtbfMttr>('GET', `${PREFIX}/bakim/metrikler?makine_id=${makineId}&gun=${gun}`),
    enabled: etkin && makineId > 0,
  });
}

/** Vade taraması (S24): vadesi gelen planlardan otomatik iş emri üretir (bir-kez). */
export function useVadeTara() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: () => istek<VadeTarama>('POST', `${PREFIX}/bakim-planlari/vade-tara`),
    onSuccess: (veri) => {
      void qc.invalidateQueries({ queryKey: BAKIM_ANAHTAR.planlar });
      void qc.invalidateQueries({ queryKey: BAKIM_ANAHTAR.ozet });
      void qc.invalidateQueries({ queryKey: ['is-emirleri'] });
      message.success(t('bakim.vade_sonuc', { adet: veri.uretilen_is_emri }));
    },
    onError: hataGoster,
  });
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
