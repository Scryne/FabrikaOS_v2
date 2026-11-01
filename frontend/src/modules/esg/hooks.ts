/** ESG veri hook'ları (S32, ADR-0051). Faktör değişince özet (emisyon) yeniden hesaplanır. */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { components } from '@/api/types.gen';

export type EsgOzet = components['schemas']['EsgOzetDTO'];
export type EsgFaktor = components['schemas']['FaktorDTO'];
export type EsgFaktorOlustur = components['schemas']['FaktorOlusturDTO'];
export type Donem = 'gun' | 'ay';

export const ESG_ANAHTAR = {
  ozet: ['esg-ozet'] as const,
  faktorler: ['esg-faktorler'] as const,
};

export function useEsgOzet(baslangic: string, bitis: string, donem: Donem) {
  const q = new URLSearchParams({ baslangic, bitis, donem });
  return useQuery({
    queryKey: [...ESG_ANAHTAR.ozet, baslangic, bitis, donem],
    queryFn: () => istek<EsgOzet>('GET', `${PREFIX}/esg/ozet?${q.toString()}`),
  });
}

export function useEsgFaktorler() {
  return useQuery({
    queryKey: ESG_ANAHTAR.faktorler,
    queryFn: () => istek<EsgFaktor[]>('GET', `${PREFIX}/esg/faktorler`),
  });
}

function useFaktorMutasyonu<T>(fn: (girdi: T) => Promise<unknown>, basariAnahtari: string) {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: fn,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ESG_ANAHTAR.faktorler });
      void qc.invalidateQueries({ queryKey: ESG_ANAHTAR.ozet });
      message.success(t(basariAnahtari));
    },
    onError: (hata: unknown) =>
      message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik')),
  });
}

export function useFaktorEkle() {
  return useFaktorMutasyonu(
    (govde: EsgFaktorOlustur) => istek<EsgFaktor>('POST', `${PREFIX}/esg/faktorler`, govde),
    'esg.faktor_eklendi',
  );
}

export function useFaktorSil() {
  return useFaktorMutasyonu(
    (id: number) => istek<unknown>('DELETE', `${PREFIX}/esg/faktorler/${id}`),
    'esg.faktor_silindi',
  );
}

/** kg → okunur: 1.234 kg altı kg, üstü ton (tr-TR). */
export function emisyonMetni(kg: number): string {
  if (Math.abs(kg) >= 1000)
    return `${(kg / 1000).toLocaleString('tr-TR', { maximumFractionDigits: 2 })} t`;
  return `${kg.toLocaleString('tr-TR', { maximumFractionDigits: 1 })} kg`;
}
