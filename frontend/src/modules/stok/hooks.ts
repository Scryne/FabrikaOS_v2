/**
 * Stok & Satınalma veri hook'ları (TanStack Query). Anahtarlar olayIsle.ts ile birebir
 * aynıdır (canlı invalidate). Mutasyonlar ilgili listeleri/detayları geçersizleştirir.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type Malzeme = components['schemas']['MalzemeCevapDTO'];
export type MalzemeOlustur = components['schemas']['MalzemeOlusturDTO'];
export type MalzemeGuncelle = components['schemas']['MalzemeGuncelleDTO'];
export type StokHareketi = components['schemas']['StokHareketiCevapDTO'];
export type StokHareketiOlustur = components['schemas']['StokHareketiOlusturDTO'];
export type SatinalmaTalebi = components['schemas']['SatinalmaTalebiCevapDTO'];
export type SatinalmaTalebiDetay = components['schemas']['SatinalmaTalebiDetayDTO'];
export type SatinalmaTalebiOlustur = components['schemas']['SatinalmaTalebiOlusturDTO'];
export type StokOzet = components['schemas']['StokOzetDTO'];
export type SatinalmaOzet = components['schemas']['SatinalmaOzetDTO'];

export const STOK_ANAHTAR = {
  malzemeler: ['malzemeler'] as const,
  malzeme: (id: number) => ['malzeme', id] as const,
  kritik: ['stok-kritik'] as const,
  hareketler: ['stok-hareketleri'] as const,
  talepler: ['satinalma-talepleri'] as const,
  talep: (id: number) => ['satinalma-talebi', id] as const,
  stokOzet: ['stok-ozet'] as const,
  satinalmaOzet: ['satinalma-ozet'] as const,
};

/** Stok KPI özeti (OzetSerit + kritik dağılımı). */
export function useStokOzet() {
  return useQuery({
    queryKey: STOK_ANAHTAR.stokOzet,
    queryFn: () => istek<StokOzet>('GET', `${PREFIX}/stok/ozet`),
  });
}

/** Satınalma KPI özeti (OzetSerit + board sayaçları). */
export function useSatinalmaOzet() {
  return useQuery({
    queryKey: STOK_ANAHTAR.satinalmaOzet,
    queryFn: () => istek<SatinalmaOzet>('GET', `${PREFIX}/satinalma/ozet`),
  });
}

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

// --- Malzeme ---
export function useMalzemeler(param: SayfaParam) {
  return useSayfaliSorgu<Malzeme>(STOK_ANAHTAR.malzemeler, '/malzemeler', param);
}

export function useMalzeme(id: number) {
  return useQuery({
    queryKey: STOK_ANAHTAR.malzeme(id),
    queryFn: () => istek<Malzeme>('GET', `${PREFIX}/malzemeler/${id}`),
    enabled: id > 0,
  });
}

export function useKritikStok() {
  return useQuery({
    queryKey: STOK_ANAHTAR.kritik,
    queryFn: () => istek<Malzeme[]>('GET', `${PREFIX}/stok/kritik`),
  });
}

/** Bu malzemenin son ``adet`` stok hareketi (bakiye trendi + giriş/çıkış kırılımı + toplamlar). */
export function useStokHareketSerisi(malzemeId: number, adet = 24) {
  return useQuery({
    queryKey: [...STOK_ANAHTAR.hareketler, malzemeId, 'seri', adet] as const,
    queryFn: () =>
      istek<StokHareketi[]>(
        'GET',
        `${PREFIX}/stok-hareketleri?malzeme_id=${malzemeId}&sayfa=1&adet=${adet}`,
      ),
    enabled: malzemeId > 0,
  });
}

export function useMalzemeOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: MalzemeOlustur) => istek<Malzeme>('POST', `${PREFIX}/malzemeler`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.malzemeler });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.stokOzet });
      message.success(t('stok.malzeme_olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useMalzemeGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: MalzemeGuncelle }) =>
      istek<Malzeme>('PATCH', `${PREFIX}/malzemeler/${id}`, govde),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.malzemeler });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.malzeme(id) });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.kritik });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.stokOzet });
      message.success(t('stok.guncellendi'));
    },
    onError: hataGoster,
  });
}

// --- Stok hareketi ---
export function useStokHareketleri(param: SayfaParam, malzemeId?: number) {
  // Filtre param.filtreler'den geçer (sorguDizesi serileştirir); path'e ?malzeme_id gömmek
  // çift `?` üretir (useSayfaliSorgu ayrıca `?` ekler → 422). Ayrı anahtar cache'i böler.
  const tamParam = malzemeId
    ? { ...param, filtreler: { ...param.filtreler, malzeme_id: malzemeId } }
    : param;
  return useSayfaliSorgu<StokHareketi>(
    malzemeId ? [...STOK_ANAHTAR.hareketler, malzemeId] : STOK_ANAHTAR.hareketler,
    '/stok-hareketleri',
    tamParam,
  );
}

export function useStokHareketEkle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: StokHareketiOlustur) =>
      istek<StokHareketi>('POST', `${PREFIX}/stok-hareketleri`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.hareketler });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.malzemeler });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.kritik });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.stokOzet });
      message.success(t('stok.hareket_eklendi'));
    },
    onError: hataGoster,
  });
}

// --- Satınalma talebi ---
export function useTalepler(param: SayfaParam) {
  return useSayfaliSorgu<SatinalmaTalebi>(STOK_ANAHTAR.talepler, '/satinalma-talepleri', param);
}

export function useTalep(id: number) {
  return useQuery({
    queryKey: STOK_ANAHTAR.talep(id),
    queryFn: () => istek<SatinalmaTalebiDetay>('GET', `${PREFIX}/satinalma-talepleri/${id}`),
    enabled: id > 0,
  });
}

/** Board için tek çekim (istemcide gruplama): en güncel 100 talep. */
export function useTalepPano() {
  return useQuery({
    queryKey: [...STOK_ANAHTAR.talepler, 'pano'],
    queryFn: () =>
      istek<SatinalmaTalebi[]>(
        'GET',
        `${PREFIX}/satinalma-talepleri?sayfa=1&adet=100&siralama=id&yon=desc`,
      ),
  });
}

export function useTalepOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: SatinalmaTalebiOlustur) =>
      istek<SatinalmaTalebiDetay>('POST', `${PREFIX}/satinalma-talepleri`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.talepler });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.satinalmaOzet });
      message.success(t('satinalma.olusturuldu'));
    },
    onError: hataGoster,
  });
}

/** Durum aksiyonu: gonder | onayla | reddet | iptal. */
export function useTalepDurumAksiyon() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({
      id,
      aksiyon,
      red_nedeni,
    }: {
      id: number;
      aksiyon: string;
      red_nedeni?: string;
    }) =>
      istek<SatinalmaTalebi>(
        'POST',
        `${PREFIX}/satinalma-talepleri/${id}/${aksiyon}`,
        aksiyon === 'reddet' ? { red_nedeni: red_nedeni ?? '' } : undefined,
      ),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.talepler });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.talep(id) });
      void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.satinalmaOzet });
      message.success(t('satinalma.durum_guncellendi'));
    },
    onError: hataGoster,
  });
}
