/**
 * CRM veri hook'ları (TanStack Query) — firma + ortak (kontak). Anahtarlar olayIsle.ts ile
 * birebir aynıdır (canlı invalidate).
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Firma = components['schemas']['FirmaCevapDTO'];
export type FirmaOlustur = components['schemas']['FirmaOlusturDTO'];
export type FirmaGuncelle = components['schemas']['FirmaGuncelleDTO'];
export type Ortak = components['schemas']['OrtakCevapDTO'];
export type OrtakOlustur = components['schemas']['OrtakOlusturDTO'];
export type TedarikciSkor = components['schemas']['TedarikciSkorDTO'];

export const CRM_ANAHTAR = {
  firmalar: ['firmalar'] as const,
  firma: (id: number) => ['firma', id] as const,
  ortaklar: (firmaId: number) => ['ortaklar', firmaId] as const,
  skor: (firmaId: number) => ['firma-skor', firmaId] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useFirmalar(param: SayfaParam) {
  return useSayfaliSorgu<Firma>(CRM_ANAHTAR.firmalar, '/firmalar', param);
}

export function useFirma(id: number) {
  return useQuery({
    queryKey: CRM_ANAHTAR.firma(id),
    queryFn: () => istek<Firma>('GET', `${PREFIX}/firmalar/${id}`),
    enabled: id > 0,
  });
}

export function useFirmaOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: FirmaOlustur) => istek<Firma>('POST', `${PREFIX}/firmalar`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: CRM_ANAHTAR.firmalar });
      message.success(t('crm.firma_olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useFirmaGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: FirmaGuncelle }) =>
      istek<Firma>('PATCH', `${PREFIX}/firmalar/${id}`, govde),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: CRM_ANAHTAR.firmalar });
      void qc.invalidateQueries({ queryKey: CRM_ANAHTAR.firma(id) });
      message.success(t('crm.guncellendi'));
    },
    onError: hataGoster,
  });
}

/** Tedarikçi performans skoru (S-VB) — 0–100 + bileşen kırılımı + dürüstlük notları. */
export function useTedarikciSkoru(firmaId: number, etkin = true) {
  return useQuery({
    queryKey: CRM_ANAHTAR.skor(firmaId),
    queryFn: () => istek<TedarikciSkor>('GET', `${PREFIX}/firmalar/${firmaId}/skor`),
    enabled: etkin && firmaId > 0,
  });
}

export function useOrtaklar(firmaId: number) {
  return useQuery({
    queryKey: CRM_ANAHTAR.ortaklar(firmaId),
    queryFn: () => istek<Ortak[]>('GET', `${PREFIX}/ortaklar?firma_id=${firmaId}`),
    enabled: firmaId > 0,
  });
}

export function useOrtakOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: OrtakOlustur) => istek<Ortak>('POST', `${PREFIX}/ortaklar`, govde),
    onSuccess: (_v, govde) => {
      void qc.invalidateQueries({ queryKey: CRM_ANAHTAR.ortaklar(govde.firma_id) });
      message.success(t('crm.ortak_eklendi'));
    },
    onError: hataGoster,
  });
}
