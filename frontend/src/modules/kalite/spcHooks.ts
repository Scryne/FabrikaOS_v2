/**
 * S26-A kalite olgunluğu hook'ları (ADR-0025): ölçüm cihazları + kalibrasyon, kontrol planları,
 * SPC kartı. Ölçüm girişi kartı ve plan özetini (son ihlal, alt grup sayısı) birlikte tazeler.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { components } from '@/api/types.gen';

export type Cihaz = components['schemas']['OlcumCihaziDTO'];
export type CihazDetay = components['schemas']['OlcumCihaziDetayDTO'];
export type Kalibrasyon = components['schemas']['KalibrasyonDTO'];
export type Plan = components['schemas']['KontrolPlaniDTO'];
export type PlanDetay = components['schemas']['KontrolPlaniDetayDTO'];
export type Karakteristik = components['schemas']['KarakteristikDTO'];
export type KarakteristikOlustur = components['schemas']['KarakteristikOlusturDTO'];

export type Gecerlilik =
  'gecerli' | 'yaklasiyor' | 'gecmis' | 'kalibrasyonsuz' | 'kullanim_disi' | 'hurda';

export const GECERLILIK_RENK: Record<Gecerlilik, string> = {
  gecerli: 'green',
  yaklasiyor: 'gold',
  gecmis: 'red',
  kalibrasyonsuz: 'default',
  kullanim_disi: 'red',
  hurda: 'default',
};

export interface SpcLimitler {
  n: number;
  alt_grup_sayisi: number;
  xbar_cl: number;
  xbar_ucl: number;
  xbar_lcl: number;
  r_cl: number;
  r_ucl: number;
  r_lcl: number;
}

export interface SpcNokta {
  sira: number;
  zaman: string;
  xbar: number;
  r: number;
  kayitli_ihlaller: { kart: string; kural: number; aciklama: string }[];
}

export interface SpcIhlal {
  kart: 'xbar' | 'r';
  kural: number;
  indeks: number;
  aciklama: string;
}

export interface SpcKart {
  karakteristik_id: number;
  plan_id: number;
  ad: string;
  birim: string;
  nominal: number | null;
  alt_tolerans: number | null;
  ust_tolerans: number | null;
  cihaz_id: number | null;
  alt_grup_boyutu: number;
  limitler_sabit: boolean;
  limitler: SpcLimitler | null;
  noktalar: SpcNokta[];
  ihlaller: SpcIhlal[];
  yetenek: { sigma_ic: number; cp: number | null; cpk: number | null } | null;
  uyarilar: string[];
}

export const SPC_ANAHTAR = {
  cihazlar: ['olcum-cihazlari'] as const,
  cihaz: (id: number) => ['olcum-cihazi', id] as const,
  planlar: ['kontrol-planlari'] as const,
  plan: (id: number) => ['kontrol-plani', id] as const,
  kart: (id: number) => ['spc-kart', id] as const,
};

function useHataBildir() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useCihazlar() {
  return useQuery({
    queryKey: SPC_ANAHTAR.cihazlar,
    queryFn: () => istek<Cihaz[]>('GET', `${PREFIX}/olcum-cihazlari`),
  });
}

export function useCihaz(id: number) {
  return useQuery({
    queryKey: SPC_ANAHTAR.cihaz(id),
    queryFn: () => istek<CihazDetay>('GET', `${PREFIX}/olcum-cihazlari/${id}`),
  });
}

export function useCihazOlustur() {
  const qc = useQueryClient();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (govde: components['schemas']['OlcumCihaziOlusturDTO']) =>
      istek<Cihaz>('POST', `${PREFIX}/olcum-cihazlari`, govde),
    onSuccess: () => void qc.invalidateQueries({ queryKey: SPC_ANAHTAR.cihazlar }),
    onError: hata,
  });
}

export function useKalibrasyonEkle(id: number) {
  const qc = useQueryClient();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (govde: components['schemas']['KalibrasyonOlusturDTO']) =>
      istek<Cihaz>('POST', `${PREFIX}/olcum-cihazlari/${id}/kalibrasyonlar`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SPC_ANAHTAR.cihaz(id) });
      void qc.invalidateQueries({ queryKey: SPC_ANAHTAR.cihazlar });
    },
    onError: hata,
  });
}

export function usePlanlar() {
  return useQuery({
    queryKey: SPC_ANAHTAR.planlar,
    queryFn: () => istek<Plan[]>('GET', `${PREFIX}/kontrol-planlari`),
  });
}

export function usePlan(id: number) {
  return useQuery({
    queryKey: SPC_ANAHTAR.plan(id),
    queryFn: () => istek<PlanDetay>('GET', `${PREFIX}/kontrol-planlari/${id}`),
  });
}

export function usePlanOlustur() {
  const qc = useQueryClient();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (govde: components['schemas']['KontrolPlaniOlusturDTO']) =>
      istek<PlanDetay>('POST', `${PREFIX}/kontrol-planlari`, govde),
    onSuccess: () => void qc.invalidateQueries({ queryKey: SPC_ANAHTAR.planlar }),
    onError: hata,
  });
}

export function useKarakteristikEkle(planId: number) {
  const qc = useQueryClient();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (govde: KarakteristikOlustur) =>
      istek<PlanDetay>('POST', `${PREFIX}/kontrol-planlari/${planId}/karakteristikler`, govde),
    onSuccess: () => void qc.invalidateQueries({ queryKey: SPC_ANAHTAR.plan(planId) }),
    onError: hata,
  });
}

export function useSpcKart(id: number) {
  return useQuery({
    queryKey: SPC_ANAHTAR.kart(id),
    queryFn: () => istek<SpcKart>('GET', `${PREFIX}/karakteristikler/${id}/kart`),
  });
}

export function useOlcumGir(id: number, planId?: number) {
  const qc = useQueryClient();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (govde: { degerler: number[]; cihaz_id?: number | null; aciklama?: string }) =>
      istek<{ sira: number; ihlaller: { kural: number; aciklama: string }[] }>(
        'POST',
        `${PREFIX}/karakteristikler/${id}/olcumler`,
        govde,
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: SPC_ANAHTAR.kart(id) });
      if (planId) void qc.invalidateQueries({ queryKey: SPC_ANAHTAR.plan(planId) });
    },
    onError: hata,
  });
}

export function useLimitSabitle(id: number) {
  const qc = useQueryClient();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (ilk?: number) =>
      istek<SpcKart>(
        'POST',
        `${PREFIX}/karakteristikler/${id}/limitleri-sabitle`,
        ilk ? { ilk } : {},
      ),
    onSuccess: (kart) => qc.setQueryData(SPC_ANAHTAR.kart(id), kart),
    onError: hata,
  });
}
