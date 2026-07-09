/** Kalite veri hook'ları (TanStack Query). Anahtarlar olayIsle.ts ile birebir aynıdır. */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type KaliteKontrol = components['schemas']['KaliteKontrolCevapDTO'];
export type KaliteKontrolOlustur = components['schemas']['KaliteKontrolOlusturDTO'];
export type Uygunsuzluk = components['schemas']['UygunsuzlukCevapDTO'];
export type UygunsuzlukDetay = components['schemas']['UygunsuzlukDetayDTO'];
export type UygunsuzlukOlustur = components['schemas']['UygunsuzlukOlusturDTO'];
export type AksiyonOlustur = components['schemas']['AksiyonOlusturDTO'];
export type KaliteOzet = components['schemas']['KaliteOzetDTO'];

export const KALITE_ANAHTAR = {
  kontroller: ['kalite-kontrolleri'] as const,
  uygunsuzluklar: ['uygunsuzluklar'] as const,
  uygunsuzlukPano: ['uygunsuzluklar', 'pano'] as const,
  uygunsuzluk: (id: number) => ['uygunsuzluk', id] as const,
  ozet: ['kalite-ozet'] as const,
};

/** Kalite/CAPA KPI özeti (OzetSerit). */
export function useKaliteOzet() {
  return useQuery({
    queryKey: KALITE_ANAHTAR.ozet,
    queryFn: () => istek<KaliteOzet>('GET', `${PREFIX}/kalite/ozet`),
  });
}

/** CAPA board için tek çekim (istemcide gruplama): en güncel 100 uygunsuzluk. */
export function useUygunsuzlukPano() {
  return useQuery({
    queryKey: KALITE_ANAHTAR.uygunsuzlukPano,
    queryFn: () =>
      istek<Uygunsuzluk[]>('GET', `${PREFIX}/uygunsuzluklar?sayfa=1&adet=100&siralama=id&yon=desc`),
  });
}

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

// --- Kalite kontrol ---
export function useKaliteKontroller(param: SayfaParam) {
  return useSayfaliSorgu<KaliteKontrol>(KALITE_ANAHTAR.kontroller, '/kalite-kontrolleri', param);
}

export function useKontrolOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: KaliteKontrolOlustur) =>
      istek<KaliteKontrol>('POST', `${PREFIX}/kalite-kontrolleri`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.kontroller });
      message.success(t('kalite.kontrol_olusturuldu'));
    },
    onError: hataGoster,
  });
}

// --- Uygunsuzluk / CAPA ---
export function useUygunsuzluklar(param: SayfaParam) {
  return useSayfaliSorgu<Uygunsuzluk>(KALITE_ANAHTAR.uygunsuzluklar, '/uygunsuzluklar', param);
}

export function useUygunsuzluk(id: number) {
  return useQuery({
    queryKey: KALITE_ANAHTAR.uygunsuzluk(id),
    queryFn: () => istek<UygunsuzlukDetay>('GET', `${PREFIX}/uygunsuzluklar/${id}`),
    enabled: id > 0,
  });
}

export function useUygunsuzlukOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: UygunsuzlukOlustur) =>
      istek<UygunsuzlukDetay>('POST', `${PREFIX}/uygunsuzluklar`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.uygunsuzluklar });
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.ozet });
      message.success(t('kalite.uygunsuzluk_olusturuldu'));
    },
    onError: hataGoster,
  });
}

export function useCapaDurum() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({
      id,
      hedef,
      kok_neden,
      dogrulama_notu,
    }: {
      id: number;
      hedef: string;
      kok_neden?: string;
      dogrulama_notu?: string;
    }) =>
      istek<Uygunsuzluk>('PATCH', `${PREFIX}/uygunsuzluklar/${id}/durum`, {
        hedef,
        kok_neden,
        dogrulama_notu,
      }),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.uygunsuzluklar });
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.ozet });
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.uygunsuzluk(id) });
      message.success(t('kalite.durum_guncellendi'));
    },
    onError: hataGoster,
  });
}

export function useAksiyonEkle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, govde }: { id: number; govde: AksiyonOlustur }) =>
      istek<UygunsuzlukDetay>('POST', `${PREFIX}/uygunsuzluklar/${id}/aksiyonlar`, govde),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.uygunsuzluk(id) });
      message.success(t('kalite.aksiyon_eklendi'));
    },
    onError: hataGoster,
  });
}

export function useAksiyonGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: ({ id, aksiyonId, durum }: { id: number; aksiyonId: number; durum: string }) =>
      istek<UygunsuzlukDetay>('PATCH', `${PREFIX}/uygunsuzluklar/${id}/aksiyonlar/${aksiyonId}`, {
        durum,
      }),
    onSuccess: (_v, { id }) => {
      void qc.invalidateQueries({ queryKey: KALITE_ANAHTAR.uygunsuzluk(id) });
      message.success(t('kalite.aksiyon_guncellendi'));
    },
    onError: hataGoster,
  });
}
