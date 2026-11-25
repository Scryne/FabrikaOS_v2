/** AI tahmin hook'ları (TanStack Query) — model kayıtları + eğitim + tür başına çıkarım. */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';

import { type ModelKaydi, type ModelTuru, type TahminCevap, TAHMIN_YOLU } from './sunum';

export const AI_ANAHTAR = {
  modeller: ['ai-modeller'] as const,
  tahmin: (tur: ModelTuru) => ['ai-tahmin', tur] as const,
};

export function useModeller() {
  return useQuery({
    queryKey: AI_ANAHTAR.modeller,
    queryFn: () => istek<ModelKaydi[]>('GET', `${PREFIX}/tahmin/modeller`),
    // Eğitim arka planda sürerken durum değişimini yakala (realtime kaçarsa da tazelenir).
    refetchInterval: (sorgu) =>
      sorgu.state.data?.some((k) => k.durum === 'egitiliyor') ? 4000 : false,
  });
}

export function useEgit() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: (tur: ModelTuru) => istek<ModelKaydi>('POST', `${PREFIX}/tahmin/egit`, { tur }),
    onSuccess: (_kayit, tur) => {
      void qc.invalidateQueries({ queryKey: AI_ANAHTAR.modeller });
      void qc.invalidateQueries({ queryKey: AI_ANAHTAR.tahmin(tur) });
      message.success(t('ai.egitim_baslatildi'));
    },
    onError: (hata) =>
      message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik')),
  });
}

/** Tür için aktif modelle çıkarım. Aktif model yoksa 404 — yeniden denenmez (beklenen durum). */
export function useTahmin(tur: ModelTuru) {
  return useQuery({
    queryKey: AI_ANAHTAR.tahmin(tur),
    queryFn: () => istek<TahminCevap>('GET', `${PREFIX}/tahmin/${TAHMIN_YOLU[tur]}`),
    // 404 (model yok) ve 503 (model deposu yok, sunucu "birazdan dene" diyor) yeniden denenmez: depo
    // erişilemezken her deneme saniyeler sürüyor, panel ~20 sn iskelette kalıyordu (2026-11-25).
    retry: (deneme, hata) =>
      !(hata instanceof ApiHata && (hata.durum === 404 || hata.durum === 503)) && deneme < 2,
  });
}

/** Sorgu hatası "aktif model yok" (404) mu? */
export function modelYok(hata: unknown): boolean {
  return hata instanceof ApiHata && hata.durum === 404;
}

export type OperatorOneri = {
  personel_id: number;
  ad_soyad: string;
  departman: string;
  unvan: string;
  skor: number;
  gerekce: string;
};

/** Operatör eşleştirme önerisi (S-VB) — kural-tabanlı, deterministik; istekle tetiklenir. */
export function useOperatorOner() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: (govde: { is_emri_id?: number; makine_id?: number; is_turu?: string }) =>
      istek<OperatorOneri[]>('POST', `${PREFIX}/tahmin/operator-eslesme`, govde),
    onError: (hata) =>
      message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik')),
  });
}
