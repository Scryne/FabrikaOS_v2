/**
 * Dış portal veri hook'ları (S18 / ADR-0020) — `/dis/*` firma-kapsamlı yüzey.
 * Firma süzgeci backend dependency'sinde zorlanır; FE yalnız kendi verisini görür.
 */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { SayfaParam } from '@/api/sayfalama';
import type { components } from '@/api/types.gen';
import { useSayfaliSorgu } from '@/modules/ortak/useSayfaliSorgu';

export type DisTalep = components['schemas']['DisTalepCevapDTO'];
export type DisTalepOlustur = components['schemas']['DisTalepOlusturDTO'];
export type DisDurum = components['schemas']['DisDurumDTO'];

export const DIS_ANAHTAR = {
  talepler: ['dis-talepler'] as const,
  durum: ['dis-durum'] as const,
};

/**
 * Kullanıcı YALNIZ dış portal kullanıcısı mı? (tek izni `dis:erisim`)
 * Girişte `/dis`'e yönlendirme kararını verir — iç izni olan (admin dahil) yönlenmez.
 */
export function sadeceDisKullanici(izinler: string[]): boolean {
  return izinler.includes('dis:erisim') && izinler.every((i) => i === 'dis:erisim');
}

export function useDisDurum() {
  return useQuery({
    queryKey: DIS_ANAHTAR.durum,
    queryFn: () => istek<DisDurum>('GET', `${PREFIX}/dis/durum`),
  });
}

export function useDisTalepler(param: SayfaParam) {
  return useSayfaliSorgu<DisTalep>(DIS_ANAHTAR.talepler, '/dis/talepler', param);
}

export function useDisTalepOlustur() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: (govde: DisTalepOlustur) =>
      istek<DisTalep>('POST', `${PREFIX}/dis/talepler`, govde),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DIS_ANAHTAR.talepler });
      void qc.invalidateQueries({ queryKey: DIS_ANAHTAR.durum });
      message.success(t('dis.talep_alindi'));
    },
    onError: (hata: unknown) =>
      message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik')),
  });
}
