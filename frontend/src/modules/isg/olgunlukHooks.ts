/**
 * S26-B İSG hook'ları (ADR-0044): eğitimler + matris, departman gereksinimleri (eğitim / KKD),
 * KKD eksikleri, acil durum tatbikatları, kaza → CAPA köprüsü.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { components } from '@/api/types.gen';

export type Egitim = components['schemas']['EgitimDTO'];
export type EgitimDetay = components['schemas']['EgitimDetayDTO'];
export type EgitimOlustur = components['schemas']['EgitimOlusturDTO'];
export type Matris = components['schemas']['MatrisDTO'];
export type Gereksinim = components['schemas']['GereksinimDTO'];
export type KkdEksik = components['schemas']['KkdEksikDTO'];
export type Tatbikat = components['schemas']['TatbikatDTO'];
export type TatbikatOlustur = components['schemas']['TatbikatOlusturDTO'];
export type KazaCapa = components['schemas']['KazaCapaDTO'];
export type GereksinimTuru = 'egitim' | 'kkd';

export const ISG26_ANAHTAR = {
  egitimler: ['isg-egitimleri'] as const,
  egitim: (id: number) => ['isg-egitimi', id] as const,
  matris: (dep?: string) => ['isg-egitim-matrisi', dep ?? ''] as const,
  gereksinimler: (tur: GereksinimTuru) => ['isg-gereksinimleri', tur] as const,
  kkd: (dep?: string) => ['kkd-eksikleri', dep ?? ''] as const,
  tatbikatlar: ['tatbikatlar'] as const,
};

function useHata() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

const dep = (d?: string) => (d ? `?departman=${encodeURIComponent(d)}` : '');

export function useEgitimler() {
  return useQuery({
    queryKey: ISG26_ANAHTAR.egitimler,
    queryFn: () => istek<Egitim[]>('GET', `${PREFIX}/isg/egitimler`),
  });
}

export function useEgitim(id: number | null) {
  return useQuery({
    queryKey: ISG26_ANAHTAR.egitim(id ?? 0),
    queryFn: () => istek<EgitimDetay>('GET', `${PREFIX}/isg/egitimler/${id}`),
    enabled: !!id,
  });
}

/** Eğitim, katılım ya da gereksinim değişince matris + KKD görünümleri birlikte tazelenir. */
function tazele(qc: ReturnType<typeof useQueryClient>) {
  void qc.invalidateQueries({ queryKey: ISG26_ANAHTAR.egitimler });
  void qc.invalidateQueries({ queryKey: ['isg-egitim-matrisi'] });
  void qc.invalidateQueries({ queryKey: ['isg-egitimi'] });
  void qc.invalidateQueries({ queryKey: ['kkd-eksikleri'] });
}

export function useEgitimOlustur() {
  const qc = useQueryClient();
  const hata = useHata();
  return useMutation({
    mutationFn: (g: EgitimOlustur) => istek<EgitimDetay>('POST', `${PREFIX}/isg/egitimler`, g),
    onSuccess: () => tazele(qc),
    onError: hata,
  });
}

export function useKatilimcilar(id: number) {
  const qc = useQueryClient();
  const hata = useHata();
  return useMutation({
    mutationFn: (personel_idler: number[]) =>
      istek<EgitimDetay>('PUT', `${PREFIX}/isg/egitimler/${id}/katilimcilar`, { personel_idler }),
    onSuccess: () => tazele(qc),
    onError: hata,
  });
}

export function useEgitimMatrisi(departman?: string) {
  return useQuery({
    queryKey: ISG26_ANAHTAR.matris(departman),
    queryFn: () => istek<Matris>('GET', `${PREFIX}/isg/egitim-matrisi${dep(departman)}`),
  });
}

export function useGereksinimler(tur: GereksinimTuru) {
  return useQuery({
    queryKey: ISG26_ANAHTAR.gereksinimler(tur),
    queryFn: () => istek<Gereksinim[]>('GET', `${PREFIX}/isg/gereksinimler/${tur}`),
  });
}

export function useGereksinimEkle(tur: GereksinimTuru) {
  const qc = useQueryClient();
  const hata = useHata();
  return useMutation({
    mutationFn: (g: { departman: string; ad: string }) =>
      istek<Gereksinim>('POST', `${PREFIX}/isg/gereksinimler/${tur}`, g),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ISG26_ANAHTAR.gereksinimler(tur) });
      tazele(qc);
    },
    onError: hata,
  });
}

export function useGereksinimSil(tur: GereksinimTuru) {
  const qc = useQueryClient();
  const hata = useHata();
  return useMutation({
    mutationFn: (id: number) => istek('DELETE', `${PREFIX}/isg/gereksinimler/${tur}/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ISG26_ANAHTAR.gereksinimler(tur) });
      tazele(qc);
    },
    onError: hata,
  });
}

export function useKkdEksikleri(departman?: string) {
  return useQuery({
    queryKey: ISG26_ANAHTAR.kkd(departman),
    queryFn: () => istek<KkdEksik[]>('GET', `${PREFIX}/isg/kkd-eksikleri${dep(departman)}`),
  });
}

export function useTatbikatlar() {
  return useQuery({
    queryKey: ISG26_ANAHTAR.tatbikatlar,
    queryFn: () => istek<Tatbikat[]>('GET', `${PREFIX}/isg/tatbikatlar`),
  });
}

export function useTatbikatOlustur() {
  const qc = useQueryClient();
  const hata = useHata();
  return useMutation({
    mutationFn: (g: TatbikatOlustur) => istek<Tatbikat>('POST', `${PREFIX}/isg/tatbikatlar`, g),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ISG26_ANAHTAR.tatbikatlar }),
    onError: hata,
  });
}

export function useKazadanCapa() {
  const qc = useQueryClient();
  const hata = useHata();
  return useMutation({
    mutationFn: (kazaId: number) =>
      istek<KazaCapa>('POST', `${PREFIX}/is-kazalari/${kazaId}/capa`, {}),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['is-kazalari'] });
      void qc.invalidateQueries({ queryKey: ['uygunsuzluklar'] });
    },
    onError: hata,
  });
}
