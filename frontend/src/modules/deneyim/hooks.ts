/**
 * S27-A hook'ları (ADR-0045): birleşik onay kutusu ve içerik araması. Onay/red kalemin
 * gösterdiği **mevcut** modül ucuna gider; başarıda kutu ve ilgili modül listeleri tazelenir.
 */

import { useTranslation } from 'react-i18next';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { App } from 'antd';

import { ApiHata, istek, PREFIX } from '@/api/client';
import type { components } from '@/api/types.gen';

export type OnayKalemi = components['schemas']['OnayKalemiDTO'];
export type OnayKutusu = components['schemas']['OnayKutusuDTO'];
export type AramaGrubu = components['schemas']['AramaGrubuDTO'];

export const ONAY_ANAHTAR = ['onaylarim'] as const;

/** Modül listelerinin anahtarları: onaylanan kalem o listelerde de durum değiştirir. */
const ILGILI: Record<string, string[][]> = {
  satinalma_talebi: [['satinalma-talepleri'], ['ticari-ozet']],
  izin_talebi: [['izin-talepleri'], ['ik-ozet'], ['izin-bakiyesi']],
  fazla_mesai: [['fazla-mesailer']],
  sayim: [['sayimlar'], ['malzemeler']],
};

export function useOnayKutusu() {
  return useQuery({
    queryKey: ONAY_ANAHTAR,
    queryFn: () => istek<OnayKutusu>('GET', `${PREFIX}/onaylarim`),
    refetchInterval: 60_000,
  });
}

export function useOnayEylemi() {
  const qc = useQueryClient();
  const { message } = App.useApp();
  const { t } = useTranslation();
  return useMutation({
    mutationFn: (v: { kalem: OnayKalemi; eylem: 'onay' | 'red'; neden?: string }) =>
      v.eylem === 'onay'
        ? istek('POST', `${PREFIX}${v.kalem.onay_yolu}`)
        : istek('POST', `${PREFIX}${v.kalem.red_yolu}`, { red_nedeni: v.neden ?? '' }),
    onSuccess: (_d, v) => {
      void qc.invalidateQueries({ queryKey: ONAY_ANAHTAR });
      for (const k of ILGILI[v.kalem.tur] ?? []) void qc.invalidateQueries({ queryKey: k });
      message.success(t(v.eylem === 'onay' ? 'onay.onaylandi' : 'onay.reddedildi'));
    },
    onError: (hata: unknown) =>
      message.error(hata instanceof ApiHata ? hata.message : t('ortak.hata_baslik')),
  });
}

export function useIcerikArama(q: string) {
  const terim = q.trim();
  return useQuery({
    queryKey: ['icerik-arama', terim],
    queryFn: () =>
      istek<AramaGrubu[]>('GET', `${PREFIX}/ara?q=${encodeURIComponent(terim)}&limit=5`),
    enabled: terim.length >= 2,
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });
}
