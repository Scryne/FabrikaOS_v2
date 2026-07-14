/**
 * Bildirim veri hook'ları (TanStack Query). Kişisel yüzey: uçlar oturum kullanıcısının
 * verisini döner (izin gerekmez). Anahtarlar olayIsle.ts ile birebir aynıdır.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { components } from '@/api/types.gen';

export type Bildirim = components['schemas']['BildirimCevapDTO'];
export type BildirimOzet = components['schemas']['BildirimOzetDTO'];
export type BildirimTercih = components['schemas']['BildirimTercihDTO'];

export const BILDIRIM_ANAHTAR = {
  liste: ['bildirimler'] as const,
  ozet: ['bildirim-ozet'] as const,
  tercihler: ['bildirim-tercihleri'] as const,
};

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

/** Zil rozeti + açılır panel beslemesi (okunmamış sayı + son 5). */
export function useBildirimOzet(etkin = true) {
  return useQuery({
    queryKey: BILDIRIM_ANAHTAR.ozet,
    queryFn: () => istek<BildirimOzet>('GET', `${PREFIX}/bildirimler/ozet`),
    enabled: etkin,
    refetchInterval: 60_000, // WS sinyali birincil; yoklama güvenlik ağı
  });
}

export function useBildirimOkundu() {
  const qc = useQueryClient();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (id: number) => istek<Bildirim>('POST', `${PREFIX}/bildirimler/${id}/okundu`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: BILDIRIM_ANAHTAR.ozet });
      void qc.invalidateQueries({ queryKey: BILDIRIM_ANAHTAR.liste });
    },
    onError: hataGoster,
  });
}

export function useTumunuOkundu() {
  const qc = useQueryClient();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: () => istek('POST', `${PREFIX}/bildirimler/tumunu-okundu`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: BILDIRIM_ANAHTAR.ozet });
      void qc.invalidateQueries({ queryKey: BILDIRIM_ANAHTAR.liste });
    },
    onError: hataGoster,
  });
}

export function useBildirimTercihleri() {
  return useQuery({
    queryKey: BILDIRIM_ANAHTAR.tercihler,
    queryFn: () => istek<BildirimTercih[]>('GET', `${PREFIX}/bildirim-tercihleri`),
  });
}

export function useTercihGuncelle() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (tercihler: BildirimTercih[]) =>
      istek<BildirimTercih[]>('PUT', `${PREFIX}/bildirim-tercihleri`, { tercihler }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: BILDIRIM_ANAHTAR.tercihler });
      message.success(t('bildirim.tercih_kaydedildi'));
    },
    onError: hataGoster,
  });
}
