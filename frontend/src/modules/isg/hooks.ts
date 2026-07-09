/** İSG veri hook'ları (TanStack Query). Anahtarlar olayIsle.ts ile birebir aynıdır. */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type IsKazasi = components['schemas']['IsKazasiCevapDTO'];
export type IsKazasiOlustur = components['schemas']['IsKazasiOlusturDTO'];
export type RiskDegerlendirme = components['schemas']['RiskDegerlendirmeCevapDTO'];
export type RiskDegerlendirmeOlustur = components['schemas']['RiskDegerlendirmeOlusturDTO'];
export type IsgOzet = components['schemas']['IsgOzetDTO'];

export const ISG_ANAHTAR = {
  kazalar: ['is-kazalari'] as const,
  riskler: ['risk-degerlendirmeleri'] as const,
  ozet: ['isg-ozet'] as const,
};

/** İSG KPI özeti (kaza + risk; RiskMatrisi hücre sayaçları dahil). */
export function useIsgOzet() {
  return useQuery({
    queryKey: ISG_ANAHTAR.ozet,
    queryFn: () => istek<IsgOzet>('GET', `${PREFIX}/isg/ozet`),
  });
}

function useHataGoster() {
  const { message } = App.useApp();
  const { t } = useTranslation();
  return (hata: unknown) =>
    message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
}

// --- İş kazası ---
export function useKazalar(param: SayfaParam) {
  return useSayfaliSorgu<IsKazasi>(ISG_ANAHTAR.kazalar, '/is-kazalari', param);
}

export function useKazaOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: IsKazasiOlustur) => istek<IsKazasi>('POST', `${PREFIX}/is-kazalari`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ISG_ANAHTAR.kazalar });
      void qc.invalidateQueries({ queryKey: ISG_ANAHTAR.ozet });
      message.success(t('isg.kaza_olusturuldu'));
    },
    onError: hataGoster,
  });
}

// --- Risk değerlendirme ---
export function useRiskler(param: SayfaParam) {
  return useSayfaliSorgu<RiskDegerlendirme>(ISG_ANAHTAR.riskler, '/risk-degerlendirmeleri', param);
}

export function useRiskOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  const hataGoster = useHataGoster();
  return useMutation({
    mutationFn: (govde: RiskDegerlendirmeOlustur) =>
      istek<RiskDegerlendirme>('POST', `${PREFIX}/risk-degerlendirmeleri`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ISG_ANAHTAR.riskler });
      void qc.invalidateQueries({ queryKey: ISG_ANAHTAR.ozet });
      message.success(t('isg.risk_olusturuldu'));
    },
    onError: hataGoster,
  });
}
