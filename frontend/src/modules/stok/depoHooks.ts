/**
 * S25-A depo/lokasyon, lokasyon bakiyesi, transfer ve sayım hook'ları (ADR-0024).
 * Mutasyonlar bakiyeleri, depo ağacını ve malzeme listelerini geçersizleştirir (toplam bakiye
 * ``Malzeme.mevcut_miktar`` da değişir).
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, istekSayfali, PREFIX } from '@/api/client';

import { STOK_ANAHTAR, type Malzeme } from './hooks';

export interface Lokasyon {
  id: number;
  depo_id: number;
  ust_lokasyon_id: number | null;
  kod: string;
  ad: string;
  aktif: boolean;
  dolu_kalem_sayisi?: number;
}

export interface Depo {
  id: number;
  kod: string;
  ad: string;
  adres: string;
  aktif: boolean;
  lokasyonlar: Lokasyon[];
}

export interface Bakiye {
  malzeme_id: number;
  malzeme_kod: string;
  malzeme_ad: string;
  birim: string;
  depo_id: number;
  depo_kod: string;
  lokasyon_id: number;
  lokasyon_kod: string;
  lot_no: string;
  miktar: number;
}

export interface SayimSatiri {
  id: number;
  malzeme_id: number;
  malzeme_kod: string | null;
  malzeme_ad: string | null;
  birim: string | null;
  lot_no: string;
  sistem_miktari: number;
  sayilan_miktar: number;
  fark: number;
  uygulanan_hareket_id: number | null;
}

export type SayimDurum = 'acik' | 'onay_bekliyor' | 'onaylandi' | 'iptal';

export const SAYIM_RENK: Record<SayimDurum, string> = {
  acik: 'processing',
  onay_bekliyor: 'warning',
  onaylandi: 'success',
  iptal: 'default',
};

export interface Sayim {
  id: number;
  kod: string;
  lokasyon_id: number;
  lokasyon_kod: string | null;
  durum: SayimDurum;
  aciklama: string;
  olusturan_kullanici_id: number | null;
  onaylayan_kullanici_id: number | null;
  onay_tarihi: string | null;
  olusturma_tarihi: string | null;
  satirlar: SayimSatiri[];
  fark_sayisi: number;
}

export const DEPO_ANAHTAR = {
  depolar: ['depolar'] as const,
  bakiyeler: (lokasyonId?: number) => ['stok-bakiyeleri', lokasyonId ?? 'tum'] as const,
  sayimlar: ['sayimlar'] as const,
  sayim: (id: number) => ['sayim', id] as const,
  malzemeSecenek: ['malzeme-secenekleri'] as const,
};

function useHataBildir() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

export function useDepolar() {
  return useQuery({
    queryKey: DEPO_ANAHTAR.depolar,
    queryFn: () => istek<Depo[]>('GET', `${PREFIX}/depolar`),
  });
}

export function useBakiyeler(lokasyonId?: number) {
  return useQuery({
    queryKey: DEPO_ANAHTAR.bakiyeler(lokasyonId),
    queryFn: () =>
      istek<Bakiye[]>(
        'GET',
        `${PREFIX}/stok-bakiyeleri${lokasyonId != null ? `?lokasyon_id=${lokasyonId}` : ''}`,
      ),
  });
}

/** Sayım satırı eklerken malzeme seçimi (ilk 200 aktif kart). */
export function useMalzemeSecenekleri() {
  return useQuery({
    queryKey: DEPO_ANAHTAR.malzemeSecenek,
    queryFn: async () =>
      (await istekSayfali<Malzeme>(`${PREFIX}/malzemeler?sayfa=1&adet=200`)).veri,
    staleTime: 60_000,
  });
}

function useStokGecersizle() {
  const qc = useQueryClient();
  return () => {
    void qc.invalidateQueries({ queryKey: ['stok-bakiyeleri'] });
    void qc.invalidateQueries({ queryKey: DEPO_ANAHTAR.depolar });
    void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.malzemeler });
    void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.hareketler });
    void qc.invalidateQueries({ queryKey: STOK_ANAHTAR.stokOzet });
  };
}

export function useLokasyonOlustur() {
  const gecersizle = useStokGecersizle();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (govde: { depo_id: number; kod: string; ad: string }) =>
      istek<Lokasyon>('POST', `${PREFIX}/lokasyonlar`, govde),
    onSuccess: gecersizle,
    onError: hata,
  });
}

export function useTransfer() {
  const gecersizle = useStokGecersizle();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (govde: {
      malzeme_id: number;
      kaynak_lokasyon_id: number;
      hedef_lokasyon_id: number;
      miktar: number;
      lot_no: string;
      aciklama?: string;
    }) => istek<unknown>('POST', `${PREFIX}/stok-transferleri`, govde),
    onSuccess: gecersizle,
    onError: hata,
  });
}

export function useSayimlar() {
  return useQuery({
    queryKey: DEPO_ANAHTAR.sayimlar,
    queryFn: () => istek<Sayim[]>('GET', `${PREFIX}/sayimlar`),
  });
}

export function useSayim(id: number) {
  return useQuery({
    queryKey: DEPO_ANAHTAR.sayim(id),
    queryFn: () => istek<Sayim>('GET', `${PREFIX}/sayimlar/${id}`),
    enabled: Number.isFinite(id),
  });
}

export function useSayimAc() {
  const qc = useQueryClient();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (govde: { lokasyon_id: number; aciklama?: string }) =>
      istek<Sayim>('POST', `${PREFIX}/sayimlar`, govde),
    onSuccess: () => void qc.invalidateQueries({ queryKey: DEPO_ANAHTAR.sayimlar }),
    onError: hata,
  });
}

export function useSayimSatirYaz(id: number) {
  const qc = useQueryClient();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (govde: { malzeme_id: number; sayilan_miktar: number; lot_no?: string }) =>
      istek<Sayim>('PUT', `${PREFIX}/sayimlar/${id}/satirlar`, govde),
    onSuccess: (sayim) => qc.setQueryData(DEPO_ANAHTAR.sayim(id), sayim),
    onError: hata,
  });
}

export function useSayimAksiyon(id: number) {
  const qc = useQueryClient();
  const gecersizle = useStokGecersizle();
  const hata = useHataBildir();
  return useMutation({
    mutationFn: (aksiyon: 'gonder' | 'onayla' | 'iptal') =>
      istek<Sayim>('POST', `${PREFIX}/sayimlar/${id}/${aksiyon}`),
    onSuccess: (sayim) => {
      qc.setQueryData(DEPO_ANAHTAR.sayim(id), sayim);
      void qc.invalidateQueries({ queryKey: DEPO_ANAHTAR.sayimlar });
      gecersizle();
    },
    onError: hata,
  });
}
