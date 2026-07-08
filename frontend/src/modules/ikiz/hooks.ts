/** Dijital ikiz veri hook'ları (TanStack Query). */

import { useTranslation } from 'react-i18next';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { components } from '@/api/types.gen';

import type { IkizDugumGiris, IkizDurumCevap } from './sunum';

export type IkizDugumCevap = components['schemas']['IkizDugumCevapDTO'];

/**
 * İkiz canlı durumu. ``yoklamaMs`` verilirse aralıklı yeniden çeker (kiosk ağ kopması
 * toparlaması); WS olayları (`makine.durum`/`uretim.eklendi`/`ikiz.yerlesim`) zaten
 * ``['ikiz']`` anahtarını geçersizleştirir.
 */
export function useIkizDurum(saat = 24, yoklamaMs?: number) {
  return useQuery({
    queryKey: ['ikiz', 'durum', saat],
    queryFn: () => istek<IkizDurumCevap>('GET', `${PREFIX}/ikiz/durum?saat=${saat}`),
    refetchInterval: yoklamaMs,
  });
}

/** Yerleşimi bütün olarak kaydeder (PUT replace-all). */
export function useYerlesimKaydet() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: (dugumler: IkizDugumGiris[]) =>
      istek<IkizDugumCevap[]>('PUT', `${PREFIX}/ikiz/yerlesim`, { dugumler }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['ikiz'] });
      message.success(t('ikiz.kaydedildi'));
    },
    onError: (hata: unknown) => {
      message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik'));
    },
  });
}
